import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import re
from dotenv import load_dotenv
import os
import html
import time

load_dotenv()


class PMQScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.theyworkforyou.com/api/getDebates"

    def fetch_pmq_debates(self, months: int = 2) -> List[Dict]:
        """
        Fetch PMQ debates for the specified number of months, handling pagination
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)

        all_debates = []
        page = 1
        while True:
            params = {
                "key": self.api_key,
                "type": "commons",
                "search": "Prime Minister Engagements",
                "num": 100,
                "page": page,
                "order": "d",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            }

            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get("rows"):  # No more results
                    break

                all_debates.extend(data["rows"])
                print(f"Fetched page {page}, got {len(data['rows'])} debates")

                page += 1
                time.sleep(1)  # Rate limiting

            except requests.exceptions.RequestException as e:
                print(f"Error fetching data on page {page}: {e}")
                break

        return all_debates

    def extract_debate_components(self, debate: Dict) -> List[Dict]:
        """
        Extract individual contributions from a debate
        """
        debate_components = []

        # Basic metadata for this debate
        base_metadata = {
            "date": debate.get("hdate"),
            "time": debate.get("htime"),
            "gid": debate.get("gid"),
            "parent_gid": debate.get("parent_gid"),
            "debate_url": f"https://www.theyworkforyou.com/debates/?id={debate.get('gid')}",
        }

        # Get the main body text and clean it
        body = debate.get("body", "")
        clean_text = html.unescape(re.sub("<[^<]+?>", "", body))

        # Extract speaker information
        speaker_info = {
            "speaker_name": debate.get("speaker", {}).get("name"),
            "speaker_party": debate.get("speaker", {}).get("party"),
            "speaker_constituency": debate.get("speaker", {}).get("constituency"),
            "speaker_id": debate.get("speaker", {}).get("member_id"),
        }

        # Create entry for this contribution
        contribution = {
            **base_metadata,
            **speaker_info,
            "text": clean_text.strip(),
            "is_question": "Q" in (debate.get("subsection", "") or ""),
            "sequence_number": debate.get("sequence_number"),
        }

        debate_components.append(contribution)

        return debate_components

    def create_dataframe(self, debates: List[Dict]) -> pd.DataFrame:
        """
        Convert debates data into a pandas DataFrame, with separate rows for each contribution
        """
        all_contributions = []

        for debate in debates:
            contributions = self.extract_debate_components(debate)
            all_contributions.extend(contributions)

        # Create DataFrame
        df = pd.DataFrame(all_contributions)

        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"])

        # Sort by date, time, and sequence number
        df = df.sort_values(
            ["date", "time", "sequence_number"], ascending=[False, True, True]
        )

        # Add question-answer grouping
        df["qa_group"] = (df["is_question"].astype(int).diff() != 0).cumsum()

        return df


def main():
    # Initialize scraper
    scraper = PMQScraper(os.getenv("THEY_WORK_FOR_YOU_API_KEY"))

    # Fetch debates with longer time period
    print("Fetching PMQ debates...")
    debates = scraper.fetch_pmq_debates(months=1)

    # Create DataFrame
    print("Processing debates into DataFrame...")
    df = scraper.create_dataframe(debates)

    # Basic info about the data
    print("\nDataFrame Info:")
    print(df.info())

    print("\nSample of the data:")
    print(df.head())

    # Print some useful summaries
    print("\nNumber of unique debates:", df["gid"].nunique())
    print("Date range:", df["date"].min(), "to", df["date"].max())
    print("Number of contributions:", len(df))

    # Save to CSV
    output_file = "data/pmq_debates.csv"
    df.to_csv(output_file, index=False)
    print(f"\nData saved to {output_file}")


if __name__ == "__main__":
    main()
