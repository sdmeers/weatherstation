from dash import Dash, html, dcc, callback, Output, Input, dash_table, State
import dash_bootstrap_components as dbc
from weather_helper import get_data, convert_wind_direction
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load live data from MYSQL server using the get_data function. CSV backup commented out
# df = pd.read_csv("/home/sdmeers/Code/weatherstation/notebooks/20240514_all_data")
df = get_data("all")

# Convert 'datetime' column to datetime type if it's not already
df['datetime'] = pd.to_datetime(df['datetime'])

# Initialize the Dash app with Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Add Font Awesome to the index string
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    <title>Weather Dashboard</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <script src="https://kit.fontawesome.com/e1d7788428.js" crossorigin="anonymous"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        .navbar-custom {
            background-color: black;
            color: white;
            padding: 10px;
        }
        .navbar-custom a {
            color: white !important;
            text-decoration: none;
        }
        .navbar-custom i {
            color: white;
            margin-right: 10px;
        }
        .navbar-custom span {
            color: white;
        }
        .center-table {
            margin-left: auto;
            margin-right: auto;
            width: 50%; /* Adjust the width as needed */
        }
        .dash-spinner, 
        ._dash-loading-spinner, 
        .dash-loading, 
        .dash-spinner-container, 
        .dash-spinner__svg, 
        .dash-debug-menu, 
        .dash-debug-menu--closed, 
        .dash-debug-menu__outer {
            display: none !important;
        }
    </style>
</head>
<body>
    <div class="navbar-custom">
        <a href="http://192.168.50.51:5000"><i class="fa fa-dashboard"></i> Weather Dashboard</a>
    </div>
    <div id="react-entry-point">
        {%app_entry%}
    </div>
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''

# Define the layout of the app
app.layout = dbc.Container([
    html.Hr(),
    dbc.Row([
        dbc.Col(html.Div("Date range "), width="auto"),
        dbc.Col(
            dcc.DatePickerRange(
                id='date-picker-range',
                start_date=df['datetime'].min(),
                end_date=df['datetime'].max(),
                display_format='YYYY-MM-DD'
            ), width="auto"
        ),
    ], align="center"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.Div(
                [
                    html.Label("Temperature", style={'font-weight': 'bold', 'margin-right': '10px'}),
                    dbc.RadioItems(
                        id='temperature-radio-items',
                        options=[
                            {'label': 'Minimum', 'value': 'min'},
                            {'label': 'Median', 'value': 'median'},
                            {'label': 'Maximum', 'value': 'max'}
                        ],
                        value='median',
                        inline=True,
                    ),
                ],
                style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '10px'}
            ),
            dcc.Graph(id='temperature-bar-chart', config={'displayModeBar': False, 'displaylogo': False}),
        ], xs=12, sm=12, md=6, lg=6, xl=6),
        dbc.Col(dcc.Graph(id='total-rainfall-bar-chart', config={'displayModeBar': False, 'displaylogo': False}), xs=12, sm=12, md=6, lg=6, xl=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='wind-direction-radar-chart', config={'displayModeBar': False, 'displaylogo': False}), xs=12, sm=12, md=6, lg=6, xl=6),
        dbc.Col(
            dash_table.DataTable(
                id='basic-statistics-table',
                columns=[
                    {"name": "Statistic", "id": "Statistic"},
                    {"name": "Value", "id": "Value"}
                ],
                style_header={
                    'whiteSpace': 'normal',
                    'textAlign': 'center'
                },
                style_table={'margin-left': 'auto', 'margin-right': 'auto', 'width': '100%'}  # Center and set width
            ), xs=12, sm=12, md=6, lg=6, xl=6
        )
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(html.Div("Display "), width="auto"),
        dbc.Col(
            dcc.Dropdown(
                id='controls-and-dropdown',
                options=[
                    {'label': 'Temperature', 'value': 'temperature'},
                    {'label': 'Humidity', 'value': 'humidity'},
                    {'label': 'Pressure', 'value': 'pressure'}
                ],
                value='temperature',
                clearable=False,
                style={'width': '200px'}
            ), width="auto"
        ),
    ], align="center"),
    html.Hr(),
    dbc.Row([
        dbc.Col(dcc.Graph(id='controls-and-graph', config={'displayModeBar': False, 'displaylogo': False}), width=12)
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(dcc.Graph(id='boxplot-graph', config={'displayModeBar': False, 'displaylogo': False}), width=12)
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col(dash_table.DataTable(
            id='statistics-table', 
            columns=[
                {"name": "Period", "id": "Period"},
                {"name": "Median Temperature (C)", "id": "Median Temperature (C)"},
                {"name": "Minimum Temperature (C)", "id": "Minimum Temperature (C)"},
                {"name": "Maximum Temperature (C)", "id": "Maximum Temperature (C)"},
                {"name": "Total Rainfall (mm)", "id": "Total Rainfall (mm)"},
                {"name": "Maximum Rain Rate (mm/s)", "id": "Maximum Rain Rate (mm/s)"},
                {"name": "Peak Windspeed (mph)", "id": "Peak Windspeed (mph)"},
            ], 
            page_size=25,
            style_header={
                'whiteSpace': 'normal',
                'textAlign': 'center'
            }
        ), width=12)
    ])
], fluid=True)

# Callback to update the graphs and tables based on selected date range and column
@callback(
    Output('temperature-bar-chart', 'figure'),
    Output('total-rainfall-bar-chart', 'figure'),
    Output('wind-direction-radar-chart', 'figure'),
    Output('basic-statistics-table', 'data'),
    Output('controls-and-graph', 'figure'),
    Output('boxplot-graph', 'figure'),
    Output('statistics-table', 'data'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('controls-and-dropdown', 'value'),
    Input('temperature-radio-items', 'value')
)
def update_graphs_and_table(start_date, end_date, col_chosen, temp_stat):
    # Filter the dataframe based on the selected date range
    filtered_df = df.loc[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].copy()
    
    # Determine the granularity for the bar charts and boxplot
    date_range = pd.to_datetime(end_date) - pd.to_datetime(start_date)
    if date_range <= timedelta(days=3):
        filtered_df['period'] = filtered_df['datetime'].dt.to_period('H').astype(str)  # Hourly
    elif date_range <= timedelta(days=14):
        filtered_df['period'] = filtered_df['datetime'].dt.to_period('D').astype(str)  # Daily
    elif date_range <= timedelta(days=92):  # Approximately 3 months
        filtered_df['period'] = filtered_df['datetime'].dt.to_period('W').astype(str)  # Weekly
    else:
        filtered_df['period'] = filtered_df['datetime'].dt.to_period('M').astype(str)  # Monthly

    # Create the temperature bar chart based on selected statistic
    if temp_stat == 'min':
        temp_df = filtered_df.groupby('period')['temperature'].min().reset_index()
    elif temp_stat == 'max':
        temp_df = filtered_df.groupby('period')['temperature'].max().reset_index()
    else:
        temp_df = filtered_df.groupby('period')['temperature'].median().reset_index()

    temp_bar_fig = px.bar(temp_df, x='period', y='temperature', title='Temperature', color_discrete_sequence=['black'])

    # Create the total rainfall bar chart
    total_rainfall_df = filtered_df.groupby('period')['rain'].sum().reset_index()
    total_rainfall_bar_fig = px.bar(total_rainfall_df, x='period', y='rain', title='Total Rainfall (mm)', color_discrete_sequence=['black'])

    # Create the wind direction radar chart
    filtered_df['wind_direction_converted'] = filtered_df['wind_direction'].apply(convert_wind_direction)
    wind_dir_counts = filtered_df['wind_direction_converted'].value_counts().reindex(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']).fillna(0).reset_index()
    wind_dir_counts.columns = ['wind_direction', 'count']
    radar_fig = go.Figure(go.Scatterpolar(
        r=wind_dir_counts['count'],
        theta=wind_dir_counts['wind_direction'],
        fill='toself',
        line=dict(color='black')
    ))
    radar_fig.update_layout(
        title='Wind Direction Count',
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90  # Rotate 90 degrees to set north at 12 o'clock
            )
        )
    )

    # Calculate basic statistics for the overall period
    filtered_df.set_index('datetime', inplace=True)
    max_daily_rainfall = filtered_df['rain'].resample('D').sum().max()

    basic_statistics = {
    "Statistic": [
        "Median Temperature (C)", 
        "Minimum Temperature (C)", 
        "Maximum Temperature (C)", 
        "Total Rainfall (mm)",
        "Maximum Daily Rainfall (mm)", 
        "Maximum Rain Rate (mm/s)",
        "Number of Rainy Days", 
        "Maximum Wind Speed (mph)" 
    ],
    "Value": [
        round(filtered_df['temperature'].median(), 1),
        round(filtered_df['temperature'].min(), 1),
        round(filtered_df['temperature'].max(), 1),
        round(filtered_df['rain'].sum(), 1),
        round(max_daily_rainfall, 1),
        round(filtered_df['rain_rate'].max() * 3600, 1),  # Convert to mm/s
        f"{(filtered_df['rain'].resample('D').sum() > 1.0).sum()}/{len(filtered_df['rain'].resample('D').sum())}",    
        round(filtered_df['wind_speed'].max() * 2.23694, 1)  # Convert to mph
    ]
}


    basic_statistics_data = pd.DataFrame(basic_statistics).to_dict('records')

    # Create the time series figure
    time_series_fig = px.scatter(
        filtered_df.reset_index(), 
        x='datetime', 
        y=col_chosen, 
        title=f'Time Series of {col_chosen.capitalize()}',
        template=None,  # Explicitly set the template to None
        color_discrete_sequence=['black']
    ).update_layout(showlegend=True)
    
    # Create the boxplot figure using Plotly Express
    boxplot_fig = px.box(
        filtered_df.reset_index(), 
        x='period', 
        y=col_chosen, 
        title=f'Box Plot of {col_chosen.capitalize()}',
        points=False,  # Do not show individual points
        template=None,  # Explicitly set the template to None
        color_discrete_sequence=['black']
    ).update_layout(showlegend=True)

    # Calculate statistics for the summary table
    statistics = filtered_df.groupby('period').agg(
        median_temperature=('temperature', 'median'),
        min_temperature=('temperature', 'min'),
        max_temperature=('temperature', 'max'),
        total_rainfall=('rain', 'sum'),
        max_rain_rate=('rain_rate', lambda x: x.max() * 3600),  # Convert to mm/s
        peak_windspeed=('wind_speed', lambda x: x.max() * 2.23694)  # Convert to mph
    ).reset_index()

    # Round the statistics to one decimal place
    statistics = statistics.round(1)

    # Rename columns for display
    statistics.columns = [
        "Period", 
        "Median Temperature (C)", 
        "Minimum Temperature (C)", 
        "Maximum Temperature (C)", 
        "Total Rainfall (mm)", 
        "Maximum Rain Rate (mm/s)", 
        "Peak Windspeed (mph)"
    ]

    statistics_data = statistics.to_dict('records')

    return temp_bar_fig, total_rainfall_bar_fig, radar_fig, basic_statistics_data, time_series_fig, boxplot_fig, statistics_data

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=5001)