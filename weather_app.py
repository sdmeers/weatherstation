from flask import Flask, render_template, request, jsonify
import mysql.connector
from weather_helper import read_data_from_db, get_data, convert_wind_direction
from datetime import datetime, timedelta
from dateutil import tz
import numpy as np
import pandas as pd
import calplot
import io
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
from matplotlib.dates import DateFormatter, DayLocator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sql_config import config
import calendar
import json

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

    #Code to plot table summarising annual data
    total_rain = year_data.groupby([year_data['datetime'].dt.month])['rain'].sum()   
    average_monthly_temperature = year_data.groupby([year_data['datetime'].dt.month])['temperature'].mean()
    max_monthly_temperature = year_data.groupby([year_data['datetime'].dt.month])['temperature'].max()
    min_monthly_temperature = year_data.groupby([year_data['datetime'].dt.month])['temperature'].min()
    #peak_wind_speed = year_data.groupby([year_data['datetime'].dt.month])['wind_speed'].max()*2.23694 
    #peak_rain_rate = year_data.groupby([year_data['datetime'].dt.month])['rain_rate'].max()*3600  

    monthly_data = {
        'Av. Temp (C)': average_monthly_temperature,
        'Max Temp (C)': max_monthly_temperature,
        'Min Temp (C)': min_monthly_temperature,
        'Total Rain (mm)': total_rain,
        #'Peak Rain (mm/s)': peak_rain_rate,
        #'Peak Wind (mph)': peak_wind_speed
    }
    
    df = pd.DataFrame(monthly_data)
    df = df.round(1)
    df.index = [calendar.month_name[month] for month in df.index]
    df_html = df.to_html(classes='w3-table-all w3-responsive', escape=False)

    #pass all the various variables to the webpage so flask can render using {{}} notation
    return render_template('current.html', 
                           time_of_latest_reading = datetime.strftime(latest_data['datetime'][0],'%A at %H:%M'),
                           latest_temperature = round(latest_data['temperature'][0],1),
                           latest_humidity = round(latest_data['humidity'][0],1), 
                           latest_rain_rate = round(latest_data['rain_rate'][0]*3600,1),
                           latest_pressure = round(latest_data['pressure'][0],1),
                           latest_luminance = round(latest_data['luminance'][0],1),
                           latest_wind_speed_mph = round(latest_data['wind_speed'][0]*2.23694,1),
                           latest_wind_direction = latest_data['wind_direction'][0],
                           latest_wind_direction_converted = convert_wind_direction(latest_data['wind_direction'][0]),
                           todays_max_temperature = round(todays_data['temperature'].max(),1),
                           todays_min_temperature = round(todays_data['temperature'].min(),1),
                           todays_total_rain = round(todays_data['rain'].sum(),1),
                           todays_average_pressure = round(todays_data['pressure'].mean(),1),
                           yesterdays_max_temperature = round(yesterdays_data['temperature'].max(),1),
                           yesterdays_min_temperature = round(yesterdays_data['temperature'].min(),1),
                           yesterdays_total_rain = round(yesterdays_data['rain'].sum(),1),
                           yesterdays_max_rain_rate = round(yesterdays_data['rain_rate'].max()*3600,1),
                           yesterdays_max_wind_speed = round(yesterdays_data['wind_speed'].max()*2.23694,1),
                           weekly_max_temperature = round(week_data['temperature'].max(),1),
                           weekly_min_temperature = round(week_data['temperature'].min(),1),
                           weekly_total_rain = round(week_data['rain'].sum(),1),
                           weekly_max_rain_rate = round(week_data['rain_rate'].max()*3600,1),
                           weekly_max_wind_speed = round(week_data['wind_speed'].max()*2.23694,1),
                           monthly_max_temperature = round(month_data['temperature'].max(),1),
                           monthly_min_temperature = round(month_data['temperature'].min(),1),
                           monthly_total_rain = round(month_data['rain'].sum(),1),
                           monthly_max_rain_rate = round(month_data['rain_rate'].max()*3600,1),
                           monthly_max_wind_speed = round(month_data['wind_speed'].max()*2.23694,1),
                           annual_max_temperature = round(year_data['temperature'].max(),1),
                           annual_min_temperature = round(year_data['temperature'].min(),1),
                           annual_total_rain = round(year_data['rain'].sum(),1),
                           annual_max_rain_rate = round(year_data['rain_rate'].max()*3600,1),
                           annual_max_wind_speed = round(year_data['wind_speed'].max()*2.23694,1),
                           table=df_html,
                           index_URL = "http://192.168.50.51/index.php"
                           )

@app.route('/weather-data', methods=['POST'])
def weather_data():
    # Extract JSON from the POST request
    data = request.get_json()
    
    # Subtract constant from temperature if needd e.g. to compensate for heating while on USB power or to adjust from garage roof to ground level (not currently used)
    data["readings"]["temperature"]=data["readings"]["temperature"]

    # Avoid writing spurious wind_speeds to the database. Assume the maximum possible is 120 mph
    if data["readings"]["wind_speed"] * 2.23694 > 120:
        data["readings"]["wind_speed"] = 0

    # Convert the timestamp string to datetime format
    utc_time = datetime.strptime(data["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=tz.tzutc())

    local_time = utc_time.astimezone(tz.gettz('Europe/London'))

    data["timestamp"] = local_time
    data["day"] = local_time.strftime("%j")
    data["week"] = local_time.strftime("%W")
    data["month"] = local_time.strftime("%m")
    data["year"] = local_time.strftime("%Y")

    # Connect to the database
    cnx = mysql.connector.connect(**config)

    # Create a cursor object
    cursor = cnx.cursor()

    # Create the INSERT INTO sql query
    add_data = ("INSERT INTO data "
                "(timestamp, temperature, pressure, humidity, rain, rain_rate, luminance, wind_speed, wind_direction, day, week, month, year) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    # Use the readings from the data
    data_tuple = (data["timestamp"], 
                data["readings"]["temperature"], 
                data["readings"]["pressure"], 
                data["readings"]["humidity"], 
                data["readings"]["rain"], 
                data["readings"]["rain_per_second"], 
                data["readings"]["luminance"], 
                data["readings"]["wind_speed"], 
                data["readings"]["wind_direction"],
                data["day"],
                data["week"],
                data["month"],
                data["year"]
                )

    # Insert the data
    cursor.execute(add_data, data_tuple)

    # Commit the transaction
    cnx.commit()

    # Close the cursor and connection
    cursor.close()
    cnx.close()

    #print('***', time, ": SUCCESS - DATA WRITTEN TO DATABASE*** ")

    # Respond with a 200 status code (OK)
    return jsonify({"message": "Data received"}), 200

@app.route('/get_data', methods=['GET'])
def get_data_api():
    try:
        # Extract parameters from request
        time_range = request.args.get('time_range', default='latest', type=str)
        
        # Call your existing get_data function
        data = get_data(time_range)
        
        # Convert DataFrame to JSON
        result = data.to_json(orient='records')
        parsed = json.loads(result)
        
        return jsonify(parsed)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500

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
    ordered_hours = sorted(xs, key=lambda x: (x - 1 - current_hour) % 24)
    ordered_ys = [ys[xs.index(x)] for x in ordered_hours]
    bar_width = 0.5
    bars = axis.bar(range(24), ordered_ys, color='black', width=bar_width)
    axis.set_xlim(-0.5, 23.5)     # Set x-axis limits to ensure no white space on the left
    ticks = [23, 17, 11, 5, 0]
    #ticks = np.arange(0, 24, 6)
    labels = [f"{ordered_hours[int(tick)]:02d}:00" for tick in ticks]
    axis.set_xticks(ticks)
    axis.set_xticklabels(labels)
    midnight_pos = ordered_hours.index(0)     # Calculate the position for midnight
    axis.axvspan(-0.5, midnight_pos, facecolor='lightgrey', alpha=0.5) # Shade from the left edge to midnight
    axis.xaxis.set_minor_locator(MultipleLocator(1))
    axis.grid(axis='y', linestyle='--', alpha=0.7)
    axis.set_ylabel(ylabel)
    y_min, y_max = axis.get_ylim()
    axis.set_ylim(0, max(1, y_max))
    # Positioning text labels in the top left and top right
    y_pos = 0.95 * axis.get_ylim()[1]  # 95% height of y-axis to place the text near the top
    axis.text(0, y_pos, 'Yesterday', ha='left', va='top', color='black')
    axis.text(23, y_pos, 'Today', ha='right', va='top')
    fig.set_facecolor('#ffffff')
    axis.set_facecolor('#ffffff')
    axis.set_title(title)
    return fig

# may need to change to calplot.yearplot to just show one year 
def plot_annual(data, how, cmap):
    fig, axis = calplot.calplot(data = data['temperature'], how = how,  figsize=(13,2.5) , cmap = cmap, linecolor='#ffffff', yearlabels=True, colorbar=False, textformat='{:.0f}')#,suptitle = title)
    fig.set_facecolor('#ffffff')
    for ax in axis.flatten():
        ax.set_facecolor('#ffffff')
    plt.rcParams['font.family'] = 'DejaVu Sans'
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