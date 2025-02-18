import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from test_yougov_TMII_raw_data import dataframes  # Import pre-loaded data

# Select the default sheet to use
default_tab = "All_adults"
df_to_plot = dataframes.get(f"yougov_TMII_{default_tab}", None)

# Filter for top issues of interest
top_issues = ["The economy", "The environment", "Health", "Immigration & Asylum", "Britain leaving the EU"]
df_filtered = df_to_plot[df_to_plot["Issue"].isin(top_issues)]

# Define a consistent color palette
palette = sns.color_palette("tab10", len(top_issues))
color_mapping = dict(zip(top_issues, palette))

# Create a grid layout for subplots
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

# Plot each issue separately with scatter and smoothed rolling average line
for i, issue in enumerate(top_issues):
    issue_df = df_filtered[df_filtered["Issue"] == issue].copy()
    issue_df["Rolling_Avg"] = issue_df["Percentage"].rolling(window=5, min_periods=1).mean()
    
    sns.scatterplot(data=issue_df, x="Date", y="Percentage", ax=axes[i], color=color_mapping[issue], alpha=0.6)
    sns.lineplot(data=issue_df, x="Date", y="Rolling_Avg", ax=axes[i], linewidth=2, color=color_mapping[issue])
    
    axes[i].set_title(issue, fontsize=12)
    axes[i].set_xlabel("Date")
    axes[i].set_ylabel("Percentage")
    axes[i].tick_params(axis="x", rotation=45)
    axes[i].grid(True, linestyle="--", alpha=0.6)

# Convert data into wide format for stacked area chart
pivot_df = df_filtered.pivot(index="Date", columns="Issue", values="Percentage").fillna(0)

# Plot all issues together as a stacked area chart
axes[5].stackplot(pivot_df.index, pivot_df.T, labels=pivot_df.columns, colors=[color_mapping[issue] for issue in pivot_df.columns], alpha=0.7)
axes[5].set_title("All Key Issues Together (Stacked Area Chart)", fontsize=12)
axes[5].set_xlabel("Date")
axes[5].set_ylabel("Percentage")
axes[5].tick_params(axis="x", rotation=45)
axes[5].legend(title="Issue", loc="upper left")
axes[5].grid(True, linestyle="--", alpha=0.6)

# Adjust layout
plt.tight_layout()
plt.show()