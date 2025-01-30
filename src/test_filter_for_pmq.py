import pandas as pd
from typing import Tuple
import re


def identify_pmq_period(df: pd.DataFrame) -> Tuple[int, int]:
    """
    Identifies the start and end indices of the PMQ period in the debate.

    Args:
        df: DataFrame containing debate data

    Returns:
        Tuple of (start_index, end_index) for the PMQ period
    """
    # Find all Prime Minister sections
    pm_sections = df[df["major_heading"] == "Prime Minister"].index

    # Group into continuous sections
    section_breaks = [
        i for i in range(1, len(pm_sections)) if pm_sections[i] - pm_sections[i - 1] > 1
    ]
    pm_ranges = []
    start = 0
    for break_idx in section_breaks + [len(pm_sections)]:
        pm_ranges.append((pm_sections[start], pm_sections[break_idx - 1]))
        start = break_idx

    # Find the main PMQ section (the one with "The Prime Minister was asked—")
    main_pmq_range = None
    for start, end in pm_ranges:
        section = df.loc[start:end]
        if (
            section["speech_content"]
            .str.contains("The Prime Minister was asked—", na=False)
            .any()
        ):
            main_pmq_range = (start, end)
            break

    if main_pmq_range is None:
        raise ValueError("Could not find main PMQ section")

    # Validate the section contains the expected structure
    pmq_section = df.loc[main_pmq_range[0] : main_pmq_range[1]]

    # Check for Q1
    q1_entries = pmq_section[pmq_section["question_number"] == "Q1"]
    if len(q1_entries) == 0:
        raise ValueError("Could not find Q1 in PMQ section")

    # Check the first question is about engagements
    q1_content = q1_entries.iloc[0]["speech_content"]
    if not re.search(r"engagements|duties", q1_content.lower()):
        raise ValueError("Q1 does not appear to be the engagements question")

    return main_pmq_range


def extract_pmq_content(file_path: str) -> pd.DataFrame:
    """
    Extracts PMQ content from a debate CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        DataFrame containing only the PMQ content
    """
    # Read the CSV file
    df = pd.read_csv(file_path)

    # Identify PMQ period
    start_idx, end_idx = identify_pmq_period(df)

    # Extract PMQ content
    pmq_content = df.loc[start_idx:end_idx].copy()

    # Add a sequence number to track the order of entries
    pmq_content["sequence_number"] = range(len(pmq_content))

    # Add section metadata
    pmq_content["section_start_marker"] = pmq_content["speech_content"].str.contains(
        "The Prime Minister was asked—", na=False
    )
    pmq_content["is_engagement_question"] = (pmq_content["question_number"] == "Q1") & (
        pmq_content["speech_content"].str.contains(
            "engagements|duties", case=False, na=False
        )
    )

    return pmq_content


def analyze_pmq_structure(pmq_df: pd.DataFrame) -> dict:
    """
    Analyzes the structure of the PMQ session.

    Args:
        pmq_df: DataFrame containing PMQ content

    Returns:
        Dictionary containing analysis results
    """
    analysis = {
        "total_entries": len(pmq_df),
        "num_questions": len(pmq_df["question_number"].dropna()),
        "num_speakers": len(pmq_df["speaker_name"].dropna().unique()),
        "speech_types": pmq_df["speech_type"].value_counts().to_dict(),
        "question_numbers": sorted(
            [
                q
                for q in pmq_df["question_number"].dropna().unique()
                if isinstance(q, str)
            ],
            key=lambda x: int(x[1:]) if x.startswith("Q") else float("inf"),
        ),
        "surrounding_context": {"previous_heading": None, "next_heading": None},
    }

    # Add validation checks
    analysis["validation"] = {
        "has_start_marker": pmq_df["section_start_marker"].any(),
        "has_engagement_question": pmq_df["is_engagement_question"].any(),
        "question_sequence_complete": True,  # Will be set to False if gaps found
    }

    # Check question number sequence
    q_numbers = [int(q[1:]) for q in analysis["question_numbers"] if q.startswith("Q")]
    if q_numbers:
        expected_sequence = set(range(1, max(q_numbers) + 1))
        actual_sequence = set(q_numbers)
        missing_numbers = expected_sequence - actual_sequence
        analysis["validation"]["question_sequence_complete"] = len(missing_numbers) == 0
        if missing_numbers:
            analysis["validation"]["missing_question_numbers"] = sorted(
                list(missing_numbers)
            )

    return analysis


def validate_pmq_extraction(df: pd.DataFrame, pmq_df: pd.DataFrame) -> dict:
    """
    Performs additional validation on the extracted PMQ content.

    Args:
        df: Original DataFrame
        pmq_df: Extracted PMQ content

    Returns:
        Dictionary containing validation results
    """
    # Find the indices in the original DataFrame
    start_idx = pmq_df.index.min()
    end_idx = pmq_df.index.max()

    # Get surrounding headings
    prev_heading = (
        df[df.index < start_idx]["major_heading"].iloc[-1] if start_idx > 0 else None
    )
    next_heading = (
        df[df.index > end_idx]["major_heading"].iloc[0]
        if end_idx < len(df) - 1
        else None
    )

    validation = {
        "preceding_heading": prev_heading,
        "following_heading": next_heading,
        "total_entries": len(pmq_df),
        "continuous_section": (pmq_df.index == range(start_idx, end_idx + 1)).all(),
    }

    return validation


if __name__ == "__main__":
    file_path = "data/debates_raw/debates2025-01-29a.csv"

    try:
        # Read original file
        df = pd.read_csv(file_path)

        # Extract PMQ content
        pmq_df = extract_pmq_content(file_path)

        # Analyze the structure
        analysis = analyze_pmq_structure(pmq_df)

        # Validate the extraction
        validation = validate_pmq_extraction(df, pmq_df)

        print("Successfully extracted PMQ content:")
        print(f"Total entries: {analysis['total_entries']}")
        print(f"Number of questions: {analysis['num_questions']}")
        print(f"Number of speakers: {analysis['num_speakers']}")
        print("\nQuestion sequence:")
        print(analysis["question_numbers"])

        print("\nValidation results:")
        print(f"Preceding heading: {validation['preceding_heading']}")
        print(f"Following heading: {validation['following_heading']}")
        print(f"Continuous section: {validation['continuous_section']}")

        if not analysis["validation"]["question_sequence_complete"]:
            print(
                "\nWarning: Missing question numbers:",
                analysis["validation"]["missing_question_numbers"],
            )

        # Save the extracted content
        output_file = "pmq_content.csv"
        pmq_df.to_csv(output_file, index=False)
        print(f"\nPMQ content saved to {output_file}")

    except Exception as e:
        print(f"Error processing file: {str(e)}")
