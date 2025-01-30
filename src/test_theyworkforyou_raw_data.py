import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import concurrent.futures
import logging
from pathlib import Path
from tqdm import tqdm

# Scrapes from https://www.theyworkforyou.com/pwdata/scrapedxml/debates/

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("parliament_scraper.log"), logging.StreamHandler()],
)


@dataclass
class DebateContext:
    oral_heading: Optional[str] = None
    major_heading: Optional[str] = None
    minor_heading: Optional[str] = None


class ParliamentaryDebateParser:
    def __init__(self, url: str):
        self.url = url
        self.context = DebateContext()

    def fetch_xml(self) -> str:
        """Fetch XML content from the URL."""
        response = requests.get(self.url)
        response.raise_for_status()
        return response.text

    def update_context(self, element: ET.Element) -> None:
        """Update the debate context based on heading elements."""
        tag = element.tag
        text = "".join(element.itertext()).strip()

        if tag == "oral-heading":
            self.context.oral_heading = text
        elif tag == "major-heading":
            self.context.major_heading = text
        elif tag == "minor-heading":
            self.context.minor_heading = text

    def extract_speech_data(self, speech_element: ET.Element) -> Dict:
        """Extract relevant data from a speech element."""
        # Get speech attributes
        attrs = speech_element.attrib

        # Extract all text from paragraphs
        paragraphs = []
        for p in speech_element.findall(".//p"):
            text = "".join(p.itertext()).strip()
            if text:
                paragraphs.append(text)

        speech_content = " ".join(paragraphs)

        # Handle column numbers more gracefully
        colnum = attrs.get("colnum", "")
        if colnum:
            try:
                colnum = int(colnum)
            except (ValueError, TypeError):
                colnum = None

        # Format timestamp consistently
        timestamp = attrs.get("time", "")
        # Extract date from URL if available
        date_str = None
        if hasattr(self, "url"):
            try:
                # Extract date from URL (format: debates2025-01-30a.xml)
                date_part = self.url.split("debates")[-1].split(".xml")[0]
                date_str = date_part[:10]  # Get YYYY-MM-DD part
            except Exception:
                pass

        if timestamp:
            try:
                # If we have a date from the URL, combine it with the time
                if date_str:
                    full_timestamp = f"{date_str} {timestamp}"
                    timestamp = pd.to_datetime(full_timestamp)
                else:
                    timestamp = pd.to_datetime(timestamp)
            except (ValueError, TypeError):
                timestamp = None

        return {
            "speech_id": attrs.get("id", ""),
            "speaker_name": attrs.get("speakername", ""),
            "speaker_id": attrs.get("person_id", ""),
            "speech_type": attrs.get("type", ""),
            "speech_content": speech_content,
            "column_number": colnum,
            "timestamp": timestamp,
            "oral_heading": self.context.oral_heading,
            "major_heading": self.context.major_heading,
            "minor_heading": self.context.minor_heading,
            "has_question_number": "oral-qnum" in attrs,
            "question_number": attrs.get("oral-qnum", ""),
        }

    def parse(self) -> pd.DataFrame:
        """Parse the XML and return a DataFrame of debate data."""
        # Fetch and parse XML
        xml_content = self.fetch_xml()
        root = ET.fromstring(xml_content)

        # Check if this is a valid debate file
        if root.tag == "publicwhip":
            latest = root.get("latest", "yes")  # Default to 'yes' if not specified
            if latest.lower() == "no":
                logging.info(f"Skipping {self.url} as it is not the latest version")
                return pd.DataFrame()  # Return empty DataFrame for non-latest versions

        # Store speech data
        speeches_data = []

        # Iterate through all elements
        for element in root.iter():
            # Update context for headings
            if element.tag in ["oral-heading", "major-heading", "minor-heading"]:
                self.update_context(element)

            # Process speech elements
            if element.tag == "speech":
                speech_data = self.extract_speech_data(element)
                speeches_data.append(speech_data)

        # Create DataFrame
        df = pd.DataFrame(speeches_data)

        # Add post-processing
        # Convert empty strings to None for cleaner data
        df = df.replace("", None)

        # Handle sorting more gracefully
        try:
            # Convert column_number to numeric, invalid parsing will produce NaN
            df["column_number"] = pd.to_numeric(df["column_number"], errors="coerce")

            # Sort by column number and speech ID to maintain chronological order
            df = df.sort_values(["column_number", "speech_id"], na_position="last")
        except Exception as e:
            logging.warning(f"Could not sort by column number: {str(e)}")
            # Fallback to just sorting by speech ID
            df = df.sort_values("speech_id")

        return df


def generate_urls(start_date: datetime, end_date: datetime) -> List[str]:
    """Generate all possible URLs between start and end dates."""
    urls = []
    current_date = start_date

    while current_date <= end_date:
        # Only scrape Wednesdays
        if current_date.weekday() != 2:  # 2 is Wednesday
            current_date += timedelta(days=1)
            continue

        # Generate URLs for each possible file suffix (a through h)
        date_str = current_date.strftime("%Y-%m-%d")
        for suffix in "abcdefgh":
            urls.append(
                f"https://www.theyworkforyou.com/pwdata/scrapedxml/debates/debates{date_str}{suffix}.xml"
            )

        current_date += timedelta(days=1)

    return urls


def process_single_url(url: str, output_dir: Path) -> Optional[pd.DataFrame]:
    """Process a single URL and return the resulting DataFrame."""
    try:
        parser = ParliamentaryDebateParser(url)
        df = parser.parse()

        # If DataFrame is empty, this was a non-latest version or redirect file
        if df.empty:
            return None

        # Add source URL and processing timestamp
        df["source_url"] = url
        df["processed_at"] = datetime.now().isoformat()

        # Save individual file
        file_name = url.split("/")[-1].replace(".xml", ".csv")
        output_path = output_dir / file_name
        df.to_csv(output_path, index=False)

        return df

    except requests.exceptions.RequestException as e:
        if (
            not isinstance(e, requests.exceptions.HTTPError)
            or e.response.status_code != 404
        ):
            logging.error(f"Error fetching {url}: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Error processing {url}: {str(e)}")
        return None


def main():
    # Configuration
    start_date = datetime(2025, 1, 1)  # Adjust as needed
    end_date = datetime(2025, 1, 31)  # Adjust as needed
    output_dir = Path("data/debates_raw")
    output_dir.mkdir(exist_ok=True)

    # Generate all possible URLs
    urls = generate_urls(start_date, end_date)
    logging.info(f"Generated {len(urls)} URLs to process")

    # Process URLs with parallel execution and progress bar
    all_dataframes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Create a progress bar
        futures = {
            executor.submit(process_single_url, url, output_dir): url for url in urls
        }

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing debates",
        ):
            url = futures[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    all_dataframes.append(df)
                    logging.info(f"Successfully processed {url}")
            except Exception as e:
                logging.error(f"Error processing {url}: {str(e)}")

    # Combine all DataFrames and save final output
    if all_dataframes:
        final_df = pd.concat(all_dataframes, ignore_index=True)

        # Ensure timestamp column is properly formatted
        final_df["timestamp"] = pd.to_datetime(final_df["timestamp"], errors="coerce")

        # Save combined output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output = output_dir / f"combined_debates_{timestamp}.csv"
        final_df.to_csv(final_output, index=False)

        # Print summary statistics with error handling
        logging.info("\nProcessing completed:")
        logging.info(f"Total speeches: {len(final_df)}")
        logging.info(f"Unique speakers: {final_df['speaker_name'].nunique()}")

        # Safely get date range
        valid_timestamps = final_df["timestamp"].dropna()
        if not valid_timestamps.empty:
            logging.info(
                f"Date range: {valid_timestamps.min()} to {valid_timestamps.max()}"
            )
        else:
            logging.info("No valid timestamps found in the data")

        # Add more detailed statistics
        logging.info("\nSpeeches per day:")
        speeches_per_day = final_df.groupby(final_df["timestamp"].dt.date).size()
        logging.info(speeches_per_day.to_string())

        logging.info(f"\nOutput saved to {final_output}")
    else:
        logging.warning("No data was successfully processed")


if __name__ == "__main__":
    main()
