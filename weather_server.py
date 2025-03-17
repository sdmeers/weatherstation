from flask import Flask, request, jsonify
import mysql.connector
from weather_helper import get_data
from datetime import datetime
from dateutil import tz
from sql_config import config, IP_addresses
import json

import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)