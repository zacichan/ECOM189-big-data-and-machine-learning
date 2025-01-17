import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import re
from dotenv import load_dotenv
import os
import html

# Load environment variables
load_dotenv()


class PMQScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.theyworkforyou.com/api/getDebates"

    def fetch_pmq_debates(self, months: int = 2) -> List[Dict]:
        """
        Fetch PMQ debates for the specified number of months
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * months)

        # Parameters for the API request
        params = {
            "key": self.api_key,
            "type": "commons",
            "search": "Prime Minister Engagements",
            "num": 100,  # Maximum results per page
            "order": "d",  # Sort by date descending
            "start_date": start_date.strftime("%Y-%m-%d"),  # Add start date
            "end_date": end_date.strftime("%Y-%m-%d"),  # Add end date
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()["rows"]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return []

    def extract_question_answer(self, debate_text: str) -> Dict[str, str]:
        """
        Extract question and answer from debate text
        """
        # Remove HTML tags
        clean_text = re.sub("<[^<]+?>", "", debate_text)

        # Decode HTML entities
        decoded_text = html.unescape(clean_text)

        # Split into paragraphs
        paragraphs = decoded_text.split("\n")

        # Combine paragraphs into single text
        return {"full_text": " ".join(paragraphs).strip()}

    def create_dataframe(self, debates: List[Dict]) -> pd.DataFrame:
        """
        Convert debates data into a pandas DataFrame
        """
        processed_debates = []

        for debate in debates:
            # Extract relevant information
            debate_data = {
                "date": debate.get("hdate"),
                "time": debate.get("htime"),
                "speaker_name": debate.get("speaker", {}).get("name"),
                "speaker_party": debate.get("speaker", {}).get("party"),
                "speaker_constituency": debate.get("speaker", {}).get("constituency"),
                "gid": debate.get("gid"),
            }

            # Extract question/answer content
            content = self.extract_question_answer(debate.get("body", ""))
            debate_data.update(content)

            processed_debates.append(debate_data)

        # Create DataFrame
        df = pd.DataFrame(processed_debates)

        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"])

        # Sort by date and time
        df = df.sort_values(["date", "time"], ascending=[False, True])

        return df


def main():
    # Initialise scraper
    scraper = PMQScraper(os.getenv("THEY_WORK_FOR_YOU_API_KEY"))

    # Fetch debates
    print("Fetching PMQ debates...")
    debates = scraper.fetch_pmq_debates(months=2)

    # Create DataFrame
    print("Processing debates into DataFrame...")
    df = scraper.create_dataframe(debates)

    # Basic info about the data
    print("\nDataFrame Info:")
    print(df.info())

    print("\nSample of the data:")
    print(df.head())

    # Save to CSV
    output_file = "data/pmq_debates.csv"
    df.to_csv(output_file, index=False)
    print(f"\nData saved to {output_file}")


if __name__ == "__main__":
    main()
