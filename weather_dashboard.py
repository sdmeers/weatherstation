from dash import Dash, html, dcc, callback, Output, Input, dash_table, State
import dash
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from weather_helper import get_data, convert_wind_direction
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
<html lang="en">
<head>
    <title>Weather Dashboard</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    <script src="https://kit.fontawesome.com/e1d7788428.js" crossorigin="anonymous"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body {
            font-family: 'Raleway', sans-serif;
            font-size: 15px;
            line-height: 1.5;
            overflow-x: hidden;
        }
        .navbar-custom {
            width: 100%;
            overflow: hidden;
            background-color: black;
            color: white;
            padding: 8px 16px;
            z-index: 4;
            position: fixed;
            top: 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 44px; /* Match height to Flask app */
        }
        .navbar-custom a {
            text-decoration: none;
            color: white !important;
            font-family: 'Raleway', sans-serif;
            font-size: 18px;
            font-weight: 400;
            display: flex;
            align-items: center;
        }
        .navbar-custom i {
            margin-right: 5px;
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
        <a href="http://192.168.50.51:5000"><i class="fa fa-dashboard"></i> Weather Summary</a>
        <a href="http://192.168.50.51/index.php"><i class="fa-solid fa-database"></i> View data</a>
    </div>
    <div id="react-entry-point" style="padding-top: 50px;">
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
        dbc.Col(
            html.Div([
                html.Button('Today', id='button-today', n_clicks=0, className='btn btn-outline-dark'),
                html.Button('Week', id='button-week', n_clicks=0, className='btn btn-outline-dark', style={'margin-left': '10px'}),
                html.Button('Month', id='button-month', n_clicks=0, className='btn btn-outline-dark', style={'margin-left': '10px'}),
                html.Button('Year', id='button-year', n_clicks=0, className='btn btn-outline-dark', style={'margin-left': '10px'}),
                html.Button('All', id='button-all', n_clicks=0, className='btn btn-outline-dark', style={'margin-left': '10px'}),
            ], style={'margin-left': '10px', 'display': 'flex', 'align-items': 'center'}),
            width="auto"
        ),
    ], align="center"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='temperature-bar-chart', config={'displayModeBar': False, 'displaylogo': False}),
            dbc.Row(
                [
                    dbc.Col(
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
                        width="auto"
                    ),
                ],
                className="justify-content-end",
                style={'margin-top': '-20px'}
            ),
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
                    {'label': 'Pressure', 'value': 'pressure'},
                    {'label': 'Rain', 'value': 'rain'},
                    {'label': 'Rain Rate', 'value': 'rain_rate'},
                    {'label': 'Wind Speed', 'value': 'wind_speed'},
                    {'label': 'Luminance', 'value': 'luminance'}
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
        dbc.Col(html.Div(
                dash_table.DataTable(
                id='statistics-table', 
                columns=[
                    {"name": "Period", "id": "Period"},
                    {"name": "Median Temperature (C)", "id": "Median Temperature (C)"},
                    {"name": "Minimum Temperature (C)", "id": "Minimum Temperature (C)"},
                    {"name": "Maximum Temperature (C)", "id": "Maximum Temperature (C)"},
                    {"name": "Total Rainfall (mm)", "id": "Total Rainfall (mm)"},
                    {"name": "Maximum Rain Rate (mm/s)", "id": "Maximum Rain Rate (mm/s)"},
                    {"name": "Peak Windspeed (mph)", "id": "Peak Windspeed (mph)"},
                    {"name": "Average Luminance (lux)", "id": "Average Luminance (lux)"}
                ], 
                page_size=25,
                style_header={
                    'whiteSpace': 'normal',
                    'textAlign': 'center'
                },
                style_table={'minWidth': '100%'}
        ), style={'overflowX': 'auto'}
    ), width=12)
    ])
], fluid=True)

# Helper function to get units based on the column chosen
def get_unit(col):
    units = {
        'temperature': 'C',
        'humidity': '%',
        'pressure': 'hPa',
        'rain': 'mm',
        'rain_rate': 'mm/s',
        'luminance': 'lux',
        'wind_speed': 'mph'
    }
    return units.get(col, '')

# Callback to update the date range when buttons are clicked
@app.callback(
    [Output('date-picker-range', 'start_date'),
     Output('date-picker-range', 'end_date')],
    [Input('button-today', 'n_clicks'),
     Input('button-week', 'n_clicks'),
     Input('button-month', 'n_clicks'),
     Input('button-year', 'n_clicks'),
     Input('button-all', 'n_clicks')]
)
def update_date_range(today, week, month, year, all):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    now = datetime.now()
    if button_id == 'button-today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        return start_date.date(), end_date
    elif button_id == 'button-week':
        start_date = now - timedelta(days=6)
        return start_date.date(), now.date()
    elif button_id == 'button-month':
        start_date = now.replace(day=1)
        return start_date.date(), now.date()
    elif button_id == 'button-year':
        start_date = now.replace(month=1, day=1)
        return start_date.date(), now.date()
    elif button_id == 'button-all':
        start_date = df['datetime'].min()
        end_date=df['datetime'].max()
        return start_date, end_date
    else:
        raise PreventUpdate

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
    Input('temperature-radio-items', 'value'),
    Input('button-refresh', 'n_clicks')  # Add the refresh button as an input
)
def update_graphs_and_table(start_date, end_date, col_chosen, temp_stat, n_clicks):
    # Fetch the fresh data whenever the button is clicked
    df = get_data("all")

    # Check if start_date and end_date are None and set default values if necessary
    if start_date is None:
        start_date = df['datetime'].min()
    else:
        start_date = pd.to_datetime(start_date)
    
    if end_date is None:
        end_date = df['datetime'].max()
    else:
        end_date = pd.to_datetime(end_date)

    # Ensure end_date includes the entire day if it's a valid date
    if pd.notna(end_date):
        end_date = (end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
    else:
        end_date = pd.to_datetime('now')

    # Filter the dataframe based on the selected date range
    filtered_df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].copy()

    logging.debug(f"update_graphs start_date: {start_date}, end_date: {end_date}") #, col_chosen: {col_chosen}, temp_stat: {temp_stat}")

    # Determine the granularity for the bar charts and boxplot
    date_range = pd.to_datetime(end_date) - pd.to_datetime(start_date)
    if date_range <= timedelta(days=2):  # Your updated condition
        period = filtered_df['datetime'].dt.floor('H')
        tickformat = '%H:%M'
    elif date_range <= timedelta(days=14):
        period = filtered_df['datetime'].dt.floor('D')
        tickformat = '%d-%b'
    elif date_range <= timedelta(days=92):  # Approximately 3 months
        period = filtered_df['datetime'].dt.to_period('W').apply(lambda r: r.start_time)
        tickformat = 'w/c %d-%b'  # Custom tick format for weeks
    else:
        period = filtered_df['datetime'].dt.to_period('M').apply(lambda r: r.start_time)
        tickformat = '%b-%Y'

    filtered_df['period'] = period

    # Create the temperature bar chart based on selected statistic
    if temp_stat == 'min':
        temp_df = filtered_df.groupby('period')['temperature'].min().reset_index()
    elif temp_stat == 'max':
        temp_df = filtered_df.groupby('period')['temperature'].max().reset_index()
    else:
        temp_df = filtered_df.groupby('period')['temperature'].median().reset_index()

    temp_bar_fig = px.bar(temp_df, x='period', y='temperature', title='Temperature', color_discrete_sequence=['black'])
    temp_bar_fig.update_layout(
        xaxis_title='', 
        yaxis_title='Temperature (C)',
        xaxis=dict(
            tickformat=tickformat,
            tickangle= -45  # Slant labels at 45 degrees
        )
    )

    # Create the total rainfall bar chart
    total_rainfall_df = filtered_df.groupby('period')['rain'].sum().reset_index()
    total_rainfall_bar_fig = px.bar(total_rainfall_df, x='period', y='rain', title='Total Rainfall', color_discrete_sequence=['black'])
    total_rainfall_bar_fig.update_layout(
        xaxis_title='', 
        yaxis_title='Rainfall (mm)',
        xaxis=dict(
            tickformat=tickformat,
            tickangle= -45  # Slant labels at 45 degrees
        )
    )

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
        title='Wind Direction',
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
            "Maximum Wind Speed (mph)"#,
            #"Average Luminance (lux)" # Average luminance doesn't really make sense in this table
        ],
        "Value": [
            round(filtered_df['temperature'].median(), 1),
            round(filtered_df['temperature'].min(), 1),
            round(filtered_df['temperature'].max(), 1),
            round(filtered_df['rain'].sum(), 1),
            round(max_daily_rainfall, 1),
            round(filtered_df['rain_rate'].max() * 3600, 1),  # Convert to mm/s
            f"{(filtered_df['rain'].resample('D').sum() > 1.0).sum()}/{len(filtered_df['rain'].resample('D').sum())}",
            round(filtered_df['wind_speed'].max() * 2.23694, 1)#,  # Convert to mph
            #round(filtered_df['luminance'].mean(), 1) # Average luminance doesn't really make sense in this table
        ]
    }

    basic_statistics_data = pd.DataFrame(basic_statistics).to_dict('records')

    # Reset the index to ensure 'datetime' is available for time series figure
    filtered_df.reset_index(inplace=True)

    # Handle y-axis titles for time series and box plots
    y_axis_title = f'{col_chosen.capitalize().replace("_", " ")} ({get_unit(col_chosen)})'
    if col_chosen == 'rain_rate':
        y_axis_title = 'Rain Rate (mm/s)'
    elif col_chosen == 'wind_speed':
        y_axis_title = 'Wind Speed (mph)'

    # Create the time series figure
    time_series_fig = px.scatter(
        filtered_df, 
        x='datetime', 
        y=filtered_df[col_chosen] * (3600 if col_chosen == 'rain_rate' else (2.23694 if col_chosen == 'wind_speed' else 1)),
        title=f'Time Series of {col_chosen.capitalize().replace("_", " ")}',
        template=None,  # Explicitly set the template to None
        color_discrete_sequence=['black']
    ).update_layout(showlegend=True)
    time_series_fig.update_layout(
        xaxis_title='', yaxis_title=y_axis_title,
        xaxis=dict(tickformat=tickformat)
    )

    if col_chosen == 'luminance':
        time_series_fig.update_yaxes(range=[0, 3000])

    # Create the boxplot figure using Plotly Express
    boxplot_fig = px.box(
        filtered_df, 
        x='period', 
        y=filtered_df[col_chosen] * (3600 if col_chosen == 'rain_rate' else (2.23694 if col_chosen == 'wind_speed' else 1)),
        title=f'Box Plot of {col_chosen.capitalize().replace("_", " ")}',
        points=False,  # Do not show individual points
        template=None,  # Explicitly set the template to None
        color_discrete_sequence=['black']
    ).update_layout(showlegend=True)
    boxplot_fig.update_layout(
        xaxis_title='', yaxis_title=y_axis_title,
        xaxis=dict(tickformat=tickformat)
    )

    if col_chosen == 'luminance':
        boxplot_fig.update_yaxes(range=[0, 3000])

    # Calculate statistics for the summary table
    statistics = filtered_df.groupby('period').agg(
        median_temperature=('temperature', 'median'),
        min_temperature=('temperature', 'min'),
        max_temperature=('temperature', 'max'),
        total_rainfall=('rain', 'sum'),
        max_rain_rate=('rain_rate', lambda x: x.max() * 3600),  # Convert to mm/s
        peak_windspeed=('wind_speed', lambda x: x.max() * 2.23694),  # Convert to mph
        avg_luminance=('luminance', 'mean')
    ).reset_index()

    # Format the 'period' column for better readability
    statistics['Period_str'] = statistics['period'].dt.strftime(tickformat)

    # Drop the original period column if it's causing the length mismatch
    statistics = statistics.drop(columns=['period'])

    # Round the statistics to one decimal place
    statistics = statistics.round(1)

    # Adjust the final DataFrame for display
    statistics_data = statistics[['Period_str', 'median_temperature', 'min_temperature', 'max_temperature', 'total_rainfall', 'max_rain_rate', 'peak_windspeed', 'avg_luminance']].to_dict('records')

    # Rename columns for display
    statistics_data = pd.DataFrame(statistics_data).rename(columns={
        "Period_str": "Period", 
        "median_temperature": "Median Temperature (C)", 
        "min_temperature": "Minimum Temperature (C)", 
        "max_temperature": "Maximum Temperature (C)", 
        "total_rainfall": "Total Rainfall (mm)", 
        "max_rain_rate": "Maximum Rain Rate (mm/s)", 
        "peak_windspeed": "Peak Windspeed (mph)",
        "avg_luminance": "Average Luminance (lux)"
    }).to_dict('records')

    #logging.debug(f"Filtered DataFrame head:\n{filtered_df.head()}")
    #logging.debug(f"Generated temp_bar_fig: {temp_bar_fig}, total_rainfall_bar_fig: {total_rainfall_bar_fig}")

    return temp_bar_fig, total_rainfall_bar_fig, radar_fig, basic_statistics_data, time_series_fig, boxplot_fig, statistics_data

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=5001)
