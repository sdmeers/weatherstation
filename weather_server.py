from flask import Flask, request, jsonify
import mysql.connector
from weather_helper import get_data
from datetime import datetime
from dateutil import tz
from sql_config import config, IP_addresses
import json
import requests

import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

app = Flask(__name__)

CLOUD_FUNCTION_URL = "https://europe-west2-weathercloud-460719.cloudfunctions.net/store-weather-data"

def send_to_cloud(data, original_timestamp):
    """
    Send weather data to Google Cloud Function
    Takes the processed data structure and original UTC timestamp
    """
    try:
        # Prepare the data for cloud storage
        cloud_data = {
            "temperature": data["readings"]["temperature"],
            "pressure": data["readings"]["pressure"], 
            "humidity": data["readings"]["humidity"],
            "rain": data["readings"]["rain"],
            "rain_rate": data["readings"]["rain_per_second"],
            "luminance": data["readings"]["luminance"],
            "wind_speed": data["readings"]["wind_speed"],
            "wind_direction": data["readings"]["wind_direction"],
            "timestamp": original_timestamp
        }
        
        # Send POST request to Cloud Function
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json=cloud_data,
            headers={'Content-Type': 'application/json'},
            timeout=10  # 10 second timeout
        )
        
        # Check if successful
        if response.status_code == 200:
            logging.info("Successfully sent data to cloud")
            return True
        else:
            logging.warning(f"Cloud function returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logging.error("Timeout sending data to cloud - continuing with local storage")
        return False
    except requests.exceptions.ConnectionError:
        logging.error("Connection error sending data to cloud - continuing with local storage")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending data to cloud: {str(e)}")
        return False

@app.route('/weather-data', methods=['POST'])
def weather_data():
    # Extract JSON from the POST request
    data = request.get_json()
    
    # Store the original timestamp for cloud storage
    original_timestamp = data["timestamp"]
    
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

    # *** NEW: Send to cloud storage ***
    # We do this early so if it fails, we still continue with local storage
    cloud_success = send_to_cloud(data, original_timestamp)
    
    # *** EXISTING: Continue with local MySQL storage ***
    try:
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
        
        # Create response message indicating both local and cloud status
        response_msg = "Data received and stored locally"
        if cloud_success:
            response_msg += " and sent to cloud"
        else:
            response_msg += " (cloud storage failed)"

        # Respond with a 200 status code (OK)
        return jsonify({"message": response_msg}), 200
        
    except mysql.connector.Error as err:
        logging.error(f"MySQL error: {err}")
        # Even if local storage fails, we might have cloud backup
        if cloud_success:
            return jsonify({"message": "Local storage failed but data sent to cloud", "error": str(err)}), 200
        else:
            return jsonify({"message": "Both local and cloud storage failed", "error": str(err)}), 500
    
    except Exception as e:
        logging.error(f"Unexpected error in weather_data: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500

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

# Optional: Add a route to test cloud connectivity
@app.route('/test-cloud', methods=['GET'])
def test_cloud():
    """Test endpoint to check if cloud function is reachable"""
    try:
        response = requests.get(CLOUD_FUNCTION_URL.replace('store-weather-data', 'get-weather-data') + '?limit=1', timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "Cloud function is reachable", "response": response.json()})
        else:
            return jsonify({"status": "Cloud function returned error", "code": response.status_code})
    except Exception as e:
        return jsonify({"status": "Cloud function not reachable", "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)