import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass


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

        return {
            "speech_id": attrs.get("id", ""),
            "speaker_name": attrs.get("speakername", ""),
            "speaker_id": attrs.get("person_id", ""),
            "speech_type": attrs.get("type", ""),
            "speech_content": speech_content,
            "column_number": attrs.get("colnum", ""),
            "timestamp": attrs.get("time", ""),
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

        # Sort by column number and speech ID to maintain chronological order
        df = df.sort_values(["column_number", "speech_id"])

        return df


def main():
    # Example usage
    url = "https://www.theyworkforyou.com/pwdata/scrapedxml/debates/debates2025-01-29a.xml"
    parser = ParliamentaryDebateParser(url)

    try:
        df = parser.parse()

        # Print basic statistics
        print(f"\nTotal speeches found: {len(df)}")
        print(f"\nUnique speakers: {df['speaker_name'].nunique()}")
        print("\nSpeech types found:")
        print(df["speech_type"].value_counts())

        # Save to CSV
        output_file = "parliamentary_debates.csv"
        df.to_csv(output_file, index=False)
        print(f"\nData saved to {output_file}")

    except Exception as e:
        print(f"Error processing debates: {str(e)}")


if __name__ == "__main__":
    main()
