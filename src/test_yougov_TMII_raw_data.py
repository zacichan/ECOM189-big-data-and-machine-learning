import pandas as pd

## Import and Transform Data

# Read in Data - no YouGov API, so just loading in excel
# Data Taken from here on 17/02/25: https://yougov.co.uk/topics/society/trackers/the-most-important-issues-facing-the-country

file_path = "/Users/rudinarendran/Documents/EMAP/ECOM189 - Big Data/Data/YouGov_TMII_250217.xlsx"
xls = pd.ExcelFile(file_path)

# Dictionary to store transformed dataframes
dataframes = {}

# Loop through all sheet names
for sheet in xls.sheet_names:
    # Read each sheet into a dataframe
    df = pd.read_excel(xls, sheet_name=sheet)

    # Rename the first column to "Issue"
    df.rename(columns={df.columns[0]: "Issue"}, inplace=True)

    # Reshape data into long format
    df_melted = df.melt(id_vars=["Issue"], var_name="Date", value_name="Percentage")

    # Convert Date column to datetime format
    df_melted["Date"] = pd.to_datetime(df_melted["Date"])

    # Remove irrelevant issues
    irrelevant_issues = ["Base", "Unweighted base", "Don't know / None of these"]
    df_melted = df_melted[~df_melted["Issue"].isin(irrelevant_issues)]

    # Handle missing values
    df_melted.dropna(subset=["Percentage"], inplace=True)

    # Convert Percentage from decimal to actual percentage scale
    df_melted["Percentage"] *= 100

    # Sort data by Date
    df_melted = df_melted.sort_values(by="Date")

    # Store the transformed dataframe
    var_name = f"yougov_TMII_{sheet.replace(' ', '_')}"  # Safe variable naming
    dataframes[var_name] = df_melted