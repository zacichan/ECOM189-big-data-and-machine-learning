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

# Plot each issue separately with the same color
for i, issue in enumerate(top_issues):
    issue_df = df_filtered[df_filtered["Issue"] == issue]
    sns.lineplot(data=issue_df, x="Date", y="Percentage", ax=axes[i], linewidth=2, color=color_mapping[issue])
    axes[i].set_title(issue, fontsize=12)
    axes[i].set_xlabel("Date")
    axes[i].set_ylabel("Percentage")
    axes[i].tick_params(axis="x", rotation=45)
    axes[i].grid(True, linestyle="--", alpha=0.6)

# Plot all issues together in the last subplot using the same colors
sns.lineplot(data=df_filtered, x="Date", y="Percentage", hue="Issue", ax=axes[5], linewidth=2, palette=color_mapping)
axes[5].set_title("All Key Issues Together", fontsize=12)
axes[5].set_xlabel("Date")
axes[5].set_ylabel("Percentage")
axes[5].tick_params(axis="x", rotation=45)
axes[5].legend(title="Issue")
axes[5].grid(True, linestyle="--", alpha=0.6)

# Adjust layout
plt.tight_layout()
plt.show()
