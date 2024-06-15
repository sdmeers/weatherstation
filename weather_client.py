from flask import Flask, render_template, request, jsonify
from weather_helper import get_data, convert_wind_direction
from datetime import datetime, timedelta
import pandas as pd
import calplot
import io
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import (MultipleLocator)
from matplotlib.dates import DayLocator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
from sql_config import IP_addresses
import calendar

import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
    latest_data = get_data("latest")
    todays_data = get_data("today")
    yesterdays_data = get_data("yesterday")
    week_data = get_data("week")
    month_data = get_data("month") #can be month=n where n=1 to 12
    year_data = get_data("year")

    # Ensure the datetime column is in datetime format
    year_data['datetime'] = pd.to_datetime(year_data['datetime'])

    # Set the datetime column as the index
    year_data.set_index('datetime', inplace=True)

    # Code to plot table summarising annual data
    total_rain = year_data.groupby(year_data.index.month)['rain'].sum()   
    average_monthly_temperature = year_data.groupby(year_data.index.month)['temperature'].mean()
    max_monthly_temperature = year_data.groupby(year_data.index.month)['temperature'].max()
    min_monthly_temperature = year_data.groupby(year_data.index.month)['temperature'].min()

    monthly_data = {
        'Av. Temp (C)': average_monthly_temperature,
        'Max Temp (C)': max_monthly_temperature,
        'Min Temp (C)': min_monthly_temperature,
        'Total Rain (mm)': total_rain,
    }

    df = pd.DataFrame(monthly_data)
    df = df.round(1)
    df.index = [calendar.month_name[month] for month in df.index]
    df_html = df.to_html(classes='w3-table-all w3-responsive', escape=False)

    num_rainy_days = (year_data['rain'].resample('D').sum() > 1.0).sum()
    total_days = len(year_data['rain'].resample('D').sum())

    return render_template('current.html', 
                           time_of_latest_reading=datetime.strftime(latest_data['datetime'][0],'%A at %H:%M'),
                           latest_temperature=round(latest_data['temperature'][0],1),
                           latest_humidity=round(latest_data['humidity'][0],1), 
                           latest_rain_rate=round(latest_data['rain_rate'][0]*3600,1),
                           latest_pressure=round(latest_data['pressure'][0],1),
                           latest_luminance=round(latest_data['luminance'][0],1),
                           latest_wind_speed_mph=round(latest_data['wind_speed'][0]*2.23694,1),
                           latest_wind_direction=latest_data['wind_direction'][0],
                           latest_wind_direction_converted=convert_wind_direction(latest_data['wind_direction'][0]),
                           todays_max_temperature=round(todays_data['temperature'].max(),1),
                           todays_min_temperature=round(todays_data['temperature'].min(),1),
                           todays_total_rain=round(todays_data['rain'].sum(),1),
                           todays_average_pressure=round(todays_data['pressure'].mean(),1),
                           yesterdays_max_temperature=round(yesterdays_data['temperature'].max(),1),
                           yesterdays_min_temperature=round(yesterdays_data['temperature'].min(),1),
                           yesterdays_total_rain=round(yesterdays_data['rain'].sum(),1),
                           yesterdays_max_rain_rate=round(yesterdays_data['rain_rate'].max()*3600,1),
                           yesterdays_max_wind_speed=round(yesterdays_data['wind_speed'].max()*2.23694,1),
                           weekly_max_temperature=round(week_data['temperature'].max(),1),
                           weekly_min_temperature=round(week_data['temperature'].min(),1),
                           weekly_total_rain=round(week_data['rain'].sum(),1),
                           weekly_max_rain_rate=round(week_data['rain_rate'].max()*3600,1),
                           weekly_max_wind_speed=round(week_data['wind_speed'].max()*2.23694,1),
                           monthly_max_temperature=round(month_data['temperature'].max(),1),
                           monthly_min_temperature=round(month_data['temperature'].min(),1),
                           monthly_total_rain=round(month_data['rain'].sum(),1),
                           monthly_max_rain_rate=round(month_data['rain_rate'].max()*3600,1),
                           monthly_max_wind_speed=round(month_data['wind_speed'].max()*2.23694,1),
                           annual_max_temperature=round(year_data['temperature'].max(),1),
                           annual_min_temperature=round(year_data['temperature'].min(),1),
                           annual_total_rain=round(year_data['rain'].sum(),1),
                           annual_max_rain_rate=round(year_data['rain_rate'].max()*3600,1),
                           annual_max_wind_speed=round(year_data['wind_speed'].max()*2.23694,1),
                           num_rainy_days=num_rainy_days,
                           total_days=total_days,
                           rainy_percent = round(100*(num_rainy_days/total_days)),
                           table=df_html,
                           index_URL=IP_addresses.get('index_URL', '192.168.0.1'),
                           dashboard_URL=IP_addresses.get('dashboard_URL', 'http://192.168.0.1')
                          )

#these functions plot are called to either plot line data or a bar chart
def plot_data(xs, ys, title, ylabel):
    fig = Figure()#figsize=(5.5,3))
    axis = fig.add_subplot(1, 1, 1)
    axis.plot(xs, ys, 'k')
    axis.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
    axis.xaxis.set_major_locator(DayLocator())
    axis.grid(axis='x', linestyle='--', alpha=0.7, which='major')
    axis.set_ylabel(ylabel)
    fig.set_facecolor('#ffffff')
    axis.set_facecolor('#ffffff')
    axis.set_title(title)
    return fig

def plot_bar(xs, ys, title, ylabel):
    fig = Figure()#figsize=(5.5,3))
    axis = fig.add_subplot(1, 1, 1)
    axis.bar(xs, ys, color=['black'])
    axis.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
    axis.xaxis.set_major_locator(mdates.DayLocator())
    axis.set_ylabel(ylabel)
    y_min, y_max = axis.get_ylim()
    axis.set_ylim(0, max(1, y_max))
    fig.set_facecolor('#ffffff')
    axis.set_facecolor('#ffffff')
    axis.set_title(title)
    return fig

def plot_daily_bar(xs, ys, title, ylabel):
    fig = Figure(figsize=(13, 2.5))
    axis = fig.add_subplot(1, 1, 1)
    axis.bar(xs, ys, color='black', width=0.5)
    ticks = range(0, 25, 6)  # We go up to 25 to include the 24th hour
    labels = [f"{tick:02d}:00" for tick in ticks] # Set x-axis ticks every 6 hours and labels in 'HH:00' format
    axis.set_xticks(ticks)
    axis.set_xticklabels(labels)
    axis.xaxis.set_minor_locator(MultipleLocator(1))
    axis.grid(axis='y', linestyle='--', alpha=0.7) # Set the y-axis gridlines
    axis.set_ylabel(ylabel)
    y_min, y_max = axis.get_ylim()
    axis.set_ylim(0, max(1, y_max))  # Setting the max y-axis value to at least 1.0 mm
    fig.set_facecolor('#ffffff')
    axis.set_facecolor('#ffffff')
    axis.set_title(title)
    return fig

def plot_24h_bar_greyed(xs, ys, title, ylabel):
    fig = Figure(figsize=(13, 2.5))
    axis = fig.add_subplot(1, 1, 1)
    current_hour = datetime.now().hour

    # Ensure all hours are present in the data
    full_xs = list(range(24))  # Hours from 0 to 23
    full_ys = [0]*24  # Default to 0 for all hours
    for x, y in zip(xs, ys):
        full_ys[x] = y

    ordered_hours = sorted(full_xs, key=lambda x: (x - 1 - current_hour) % 24)     # Order hours based on current hour
    ordered_ys = [full_ys[x] for x in ordered_hours]

    bar_width = 0.5
    axis.bar(range(24), ordered_ys, color='black', width=bar_width)
    axis.set_xlim(-0.5, 23.5)     # Set x-axis limits to ensure no white space on the left
    ticks = [23, 17, 11, 5, 0]
    labels = [f"{ordered_hours[int(tick)]:02d}:00" for tick in ticks]
    axis.set_xticks(ticks)
    axis.set_xticklabels(labels)
    midnight_pos = ordered_hours.index(0)     # Calculate the position for midnight
    axis.axvspan(-0.5, midnight_pos, facecolor='lightgrey', alpha=0.5) # Shade from the left edge to midnight
    axis.xaxis.set_minor_locator(MultipleLocator(1))
    axis.grid(axis='y', linestyle='--', alpha=0.7)
    axis.set_ylabel(ylabel)
    axis.set_ylim(0, max(1, axis.get_ylim()[1]))
    axis.text(0, axis.get_ylim()[1] * 0.95, 'Yesterday', ha='left', va='top')
    axis.text(23, axis.get_ylim()[1] * 0.95, 'Today', ha='right', va='top')
    fig.subplots_adjust(left=0.045, right=0.98, top=0.9, bottom=0.2) # Adjust the subplot parameters to reduce whitespace padding either side
    fig.set_facecolor('#ffffff')
    axis.set_facecolor('#ffffff')
    axis.set_title(title)

    return fig

# these functions plot each graph. One is needed per graph
@app.route('/plot_temperature.png')
def plot_temperature_png():
    data = get_data("last7days")
    fig = plot_data(data['datetime'], data['temperature'].rolling(window=5).mean(), 'Temperature', 'Temperature (C)')
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_humidity.png')
def plot_humidity_png():
    data = get_data("last7days")
    fig = plot_data(data['datetime'], data['humidity'].rolling(window=5).mean(), 'Humidity', 'Humidity (%)')
    fig.gca().set_ylim(0,100)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_pressure.png')
def plot_pressure_png():
    data = get_data("last7days")
    fig = plot_data(data['datetime'], data['pressure'], 'Pressure', 'Pressure (hPa)')
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_daily_rainfall.png')
def plot_daily_rainfall_png():
    todays_data = get_data("today")
    rain_data = todays_data.groupby([todays_data['datetime'].dt.hour])['rain'].sum()
    fig = plot_daily_bar(rain_data.index, rain_data, "Rainfall", "Rainfall (mm)")
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_24h_rainfall.png')
def plot_24h_rainfall_png():
    last24h_data = get_data("last24h")  # Fetch data for the last 24 hours
    rain_data = last24h_data.groupby([last24h_data['datetime'].dt.hour])['rain'].sum()   
    fig = plot_24h_bar_greyed(list(rain_data.index), list(rain_data.values), "Hourly Rainfall", "Rainfall (mm)")
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_rain.png')
def plot_rain_png():
    last_7_days_data = get_data("last7days")
    rain_data = last_7_days_data[['datetime','rain']].groupby(last_7_days_data['datetime'].dt.date)['rain'].sum()
    rain_data.index = pd.to_datetime(rain_data.index, format='%Y-%m-%d')
    fig = plot_bar(rain_data.index, rain_data, "Rainfall", "Rainfall (mm)")
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_annual_max_temperatures.png')
def plot_annual_max_temperatures_png():
    data = get_data("year")
    data.set_index('datetime', inplace = True)
    fig = plot_annual(data, 'max', 'coolwarm')
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

# may need to change to calplot.yearplot to just show one year 
def plot_annual(data, how, cmap):
    fig, axis = calplot.calplot(data = data['temperature'], how = how,  figsize=(13,2.5) , cmap = cmap, linecolor='#ffffff', yearlabels=True, colorbar=False, textformat='{:.0f}')#,suptitle = title)
    fig.set_facecolor('#ffffff')
    for ax in axis.flatten():
        ax.set_facecolor('#ffffff')
    plt.rcParams['font.family'] = 'DejaVu Sans'
    return fig

@app.route('/plot_annual_rain_days.png')
def plot_annual_rain_days_png():
    data = get_data("year")
    data.set_index('datetime', inplace=True)

    # Aggregate rain data to get binary values: 1 if rain occurred, 0 otherwise
    rain_data = data['rain'].resample('D').sum() > 1  # True if more than 1mm rain occurred on that day
    rain_data = rain_data.astype(int)  # Convert boolean to int (1 for True, 0 for False)

    # Create a custom colormap for binary data (0: transparent, 1: black)
    cmap = mcolors.ListedColormap(['#f0f0f0', 'black'])

    # Create the calplot with the same parameters as plot_annual
    fig, axis = calplot.calplot(data=rain_data, how='sum', figsize=(13, 2.5), cmap=cmap, linecolor='#ffffff', yearlabels=True, colorbar=False, vmin = 0, vmax = 1)
    fig.set_facecolor('#ffffff')
    for ax in axis.flatten():
        ax.set_facecolor('#ffffff')
    plt.rcParams['font.family'] = 'DejaVu Sans'

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/plot_annual_min_temperatures.png')
def plot_annual_min_temperatures_png():
    data = get_data("year")
    data.set_index('datetime', inplace = True)
    fig = plot_annual(data, 'min', 'Blues')
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
