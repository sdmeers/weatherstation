# Overview
This respository contains the files necessary to run a webserver that runs with a [Enviro Weather](https://github.com/pimoroni/enviro). The webserver is designed to run as a service on a Raspberry Pi and provides the HTTP Endpoints to accept the readings from the Enviro Weather and store them in a MySQL database. It also serves responsive webpages to view the recorded data as shown in the following screenshots.

![Screenshot of the web interface displaying the weather data including current temperature, humidity, pressure and more.](https://github.com/sdmeers/weatherstation/blob/main/screenshots/weatherstation-screenshot.jpg)

As well as the most recently recorded data the webpages plot historic weather data for both the past 24 hours rainfall and also the last 7 days of temperature, humidity, pressure and daily rainfall.

![Screenshot of the web interface plotting historiic  weather data including current temperature, humidity, pressure and more.](https://github.com/sdmeers/weatherstation/blob/main/screenshots/weatherstation-graphs.jpg)

A link is provided in the top left to an interactive dashboard (runs on port:5001) which enables the data to be analysed for any given time period. A basic summary is provided at the top of the screen and more detailed analysis is possible at the bottom including the ability to select a number of different data fields for more detailed analysis.

![Screenshot of the interactive dashboard enabling detailed analysis temperature, humidity, pressure and more for a given date range.](https://github.com/sdmeers/weatherstation/blob/main/screenshots/dashboard_screenshot.jpg)

In the top right a link is provided to view the data stored in the database. Each page contains a day of data, 96 readings i.e. every 15 minutes.

![Screenshot of the page to view the data stored in the database.](https://github.com/sdmeers/weatherstation/blob/main/screenshots/raw_data.jpg)

## Installation

The webserver is designed to run on a Raspberry Pi and has been developed using Python 3.11.3. This is a home project for fun, it works reliably but may need some modification to work on your system. There are probably many ways to improve it - grateful for any suggestions!

### Step 0: Config the Enviro Weather and specify the IP address for the HTTP Endpoint
Setup the Enviro Weather as described [here](https://github.com/pimoroni/enviro/blob/main/documentation/getting-started.md) adding the IP address of the Raspberry Pi as the custom HTTP endpoint. Taking readings every 15 minutes is recommended.

### Step 1: Clone this repository to ~/weather & install the necessary Python libraries 
These are described in the `requirements.txt` file. Simply run

```.bash
git clone https://github.com/sdmeers/weatherstation
cd weatherstation
pip install -r requirements.txt
```

Then copy `index.php` into `/var/www/html/`. 



### Step 2: Install MySQL on the server
The weather records are stored in a MySQL database which is recommended to run on a remote Raspberry Pi or similar. Follow the installation instructions [here](https://pimylifeup.com/raspberry-pi-mysql/).

### Step 3: Create a SQL table to store the necessary data

Login to MySQL as root user and create a new database called `weather` and switch to use that database.

```
sudo mysql -u root -p
CREATE DATABASE weather;
USE weather;
```

Finally create a new table called `data` within the database using the following command. This table will store the data sent from the weatherstation.

```
CREATE TABLE IF NOT EXISTS `data` (
  id INT AUTO_INCREMENT PRIMARY KEY,
  timestamp DATETIME NOT NULL,
  temperature DOUBLE(4,2) NOT NULL,
  pressure DOUBLE(6,2) NOT NULL,
  humidity DOUBLE(3,1) NOT NULL,
  rain DOUBLE(6,2) NOT NULL,
  rain_rate DOUBLE(6,5) NOT NULL,
  luminance DOUBLE(7,2) NOT NULL,
  wind_speed DOUBLE(3,1) NOT NULL,
  wind_direction DOUBLE(3,0) NOT NULL,
  day int(3) NOT NULL,
  week int(2) NOT NULL,
  month int(2) NOT NULL,
  year int(4) NOT NULL
);
```

Depending on your user permissions it may be necessary to update privileges using

```
CREATE USER 'myuser'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON weather.* TO 'myuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;

```

### Step 4: Create the necessary config files 
Add your MySQL `<username>` and `<password>` to the two config files using the templates above [sql_config-template.py](https://github.com/sdmeers/weatherstation/blob/main/sql_config-template.py) and [config-template.php](https://github.com/sdmeers/weatherstation/blob/main/config-template.php). Rename both files remove the `-template` suffix and add the `<IP_address>` of the web server to `sql_config.py`.

### Step 5: Run the necessary services in the background on Linux

There are three linked services to run the app as follows: 
* Server: accepts the post requests from the enviro and writes them into the MySQL database.
* Client: Flask app that serves the summary webpage.
* Dashboard: Plotly-Dash app that runs the interactive dashboard.

The 3 x .service files (`<weather_client/server/dashboard.service>`) will need to be modified. Follow the process below, repeating for the `weather_server` and `weather_dashboard` services.   

* Edit [weather_client.service](https://github.com/sdmeers/weatherstation/blob/main/weather_client.service) with your path to `weather_client.py`. The line you will need to edit is as follows.

```
ExecStart=/usr/bin/python3 <path_to_python_file.py>

e.g.
ExecStart=/usr/bin/python3 /home/pi/weatherstation/weather_client.py
```

* Save this file to `/etc/systemd/system/weather_client.service`
* Reload the systemd daemon to recognize your new service

```
sudo systemctl daemon-reload
```

* Enable the service to start on boot

```
sudo systemctl enable weather_client.service
```

* Start the service immediately without rebooting

```
sudo systemctl start weather_client.service
```

This will run the webserver as a background service on boot enabling it to accept data from the Enviro Weather. 

### Step 6: Use the webserver to view the data  

The webpages to display the weather data can be accessed via `localhost:5001` or `<IP_address>:5001`. You should something similar to the screenshot below.

![Screenshot of the full web interface show current & historic weather data](https://github.com/sdmeers/weatherstation/blob/main/screenshots/weatherstation-full.jpg)

## Useful  commands 
Check the status of your service:

```
sudo systemctl status weather_client.service
```

Stop, restart & disable your service:

```
sudo systemctl stop weather_client.service
sudo systemctl restart weather_client.service
sudo systemctl disable weather_client.service
```

View the most recent 50 log entries via syslog 

```
journalctl -n 50 -u weather_client.service
```
MySQL command to exporting SQL Data to csv

```
sudo mysql -u root -p
USE weather;

SELECT *
FROM data
INTO OUTFILE '/tmp/weather_data_export.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';
```

## Other notes
A script to convert the weather direction readings from the Enviro Weather (in degrees) to compass cardinal points (N, NE etc...) is included in the [weather_helper.py](https://github.com/sdmeers/weatherstation/blob/main/weather_helper.py). Use a compass to determine how to modify the values in the helper file depending on how your weatherstation is oriented.

A link is provided to `index.php` which displays the raw data from the MySQL database. Each page shows 96 records which corresponds to 24 hours of data sampled every 15 minutes.

The Enviro Weather requires a static IP for the web-server (this also makes it easier to access the web-pages). If running on a local network use IP Binding on the router to ensure the web-server is allocated a static IP.  

An `update_pi` script is included to make it easy to copy files from a development laptop across to the remote server (e.g. the Raspberry Pi) using scp. Simply run `./update_pi`. You'll need to edit the file to add the IP address of the remote server (also rename to remove the '-template' suffix). You'll also need to have set up `ssh` to enable this script.    

## Helper functions
[weather_helper.py](https://github.com/sdmeers/weatherstation/blob/main/weather_helper.py) contains a number of helper Python functions. In particular the `get_data(**args)` function is included to simplify the extraction of weather records from the MySQL database as a Pandas DataFrame, for example for analysis of the data in a Jupyter Notebook. A summary of the help page for the function is as follows:

```
get_data(*args):
    Fetches data from a database based on the provided time range criteria.

    Parameters:
        *args : variable length argument list.
            - Can be a single string that defines the time range:
                - "latest": Returns the most recent record.
                - "today": Returns data for the current day.
                - "last24h": Returns data for the last 24 hours.
                - "yesterday": Returns data for the previous day.
                - "day=n": Returns data for the nth day of the current year (n: 1-366).
                - "week": Returns data for the current week starting from Monday.
                - "week=n": Returns data for the nth week of the year (n: 1-53).
                - "last7days": Returns data for the last 7 days.
                - "month": Returns data for the current month.
                - "month=n": Returns data for the nth month (n: 1-12).
                - "year": Returns data for the entire current year.
                - "year=n": Returns data for the specified year.
                - "all": Returns all the data in the database.
            - Or two datetime objects defining the start and end dates for the data fetch.

    Returns:
        pd.DataFrame: A DataFrame containing data fetched from the database.
``` 
