import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import datetime

from test_yougov_TMII_raw_data import dataframes  # Import pre-loaded data

# Define categories for filters
age_groups = ["18-24", "25-49", "50-64", "65+"]
gender_groups = ["Male", "Female"]
political_groups = ["Conservative", "Labour", "Liberal Democrat"]
region_groups = ["London", "Rest of South", "Midlands", "North", "Scotland", "Wales"]
social_grade_groups = ["AB, C1", "C2, D, E"]

# Select the default sheet to visualize (changeable)
default_tab = "All_adults"
df_to_plot = dataframes.get(f"yougov_TMII_{default_tab}", None)

## Dash App for Interactive Visualization
app = dash.Dash(__name__)

# Define min and max dates for the slider
min_date = df_to_plot["Date"].min()
max_date = df_to_plot["Date"].max()

app.layout = html.Div([
    html.H1(f"YouGov: The most important issues facing the country"),
    html.P("Note: You can only select one category at a time (Age, Gender, Politics, Region, or Social Grade). Selecting multiple will default to the first valid selection."),
    dcc.Dropdown(
        id='age-selector',
        options=[{'label': age, 'value': age} for age in age_groups],
        value=None,
        placeholder="Select Age Group",
    ),
    dcc.Dropdown(
        id='gender-selector',
        options=[{'label': gender, 'value': gender} for gender in gender_groups],
        value=None,
        placeholder="Select Gender",
    ),
    dcc.Dropdown(
        id='political-selector',
        options=[{'label': party, 'value': party} for party in political_groups],
        value=None,
        placeholder="Select Political Affiliation",
    ),
    dcc.Dropdown(
        id='region-selector',
        options=[{'label': region, 'value': region} for region in region_groups],
        value=None,
        placeholder="Select Region",
    ),
    dcc.Dropdown(
        id='social-grade-selector',
        options=[{'label': grade, 'value': grade} for grade in social_grade_groups],
        value=None,
        placeholder="Select Social Grade",
    ),
    dcc.Dropdown(
        id='issue-selector',
        options=[{'label': issue, 'value': issue} for issue in df_to_plot["Issue"].unique()],
        value=df_to_plot["Issue"].unique().tolist(),  # Display all issues by default
        multi=True
    ),
    dcc.RangeSlider(
        id='date-slider',
        min=min_date.timestamp(),
        max=max_date.timestamp(),
        value=[min_date.timestamp(), max_date.timestamp()],
        marks={int(date.timestamp()): date.strftime('%Y-%m') for date in pd.date_range(min_date, max_date, freq='6M')},
        step=None,
        tooltip={"always_visible": True}
    ),
    dcc.Graph(id='line-chart', style={'height': '700px'})
])

@app.callback(
    Output('line-chart', 'figure'),
    [Input('issue-selector', 'value'),
     Input('age-selector', 'value'),
     Input('gender-selector', 'value'),
     Input('political-selector', 'value'),
     Input('region-selector', 'value'),
     Input('social-grade-selector', 'value'),
     Input('date-slider', 'value')]
)
def update_chart(selected_issues, age, gender, political, region, social_grade, date_range):
    # Ensure only one filter is applied at a time
    selected_tab = "All_adults"
    for group in [age, gender, political, region, social_grade]:
        if group is not None:
            selected_tab = group
            break
    
    df_filtered = dataframes.get(f"yougov_TMII_{selected_tab}", df_to_plot)
    df_filtered = df_filtered[df_filtered["Issue"].isin(selected_issues)]
    df_filtered = df_filtered[(df_filtered["Date"] >= datetime.datetime.fromtimestamp(date_range[0])) & 
                              (df_filtered["Date"] <= datetime.datetime.fromtimestamp(date_range[1]))]
    
    fig = go.Figure()
    for issue in selected_issues:
        issue_df = df_filtered[df_filtered["Issue"] == issue]
        fig.add_trace(go.Scatter(
            x=issue_df["Date"],
            y=issue_df["Percentage"],
            mode='lines+markers',
            name=issue,
            hovertemplate='<b>%{y:.1f}%</b><br>%{x|%d-%b-%Y}<extra>' + issue + '</extra>'
        ))
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Percentage of People Selecting Issue",
        yaxis_tickformat=".0f%%",
        hovermode="x unified",
        template="plotly_white",
        height=700
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
