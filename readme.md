# Overview
This respository contains the files necessary to run a webserver that runs with a Enviro Weather. The webserver is designed to run as a service on a Raspberry Pi and provides the HTTP Endpoints to accept the readings from the Enviro Weather and store them in a MySQL database. It also serves responsive webpages to view the recorded data as shown in the following screenshots 
![Screenshot of the web interface displaying the weather data including current temperature, humidity, pressure and more.](https://github.com/sdmeers/weatherstation/blob/main/weatherstation-screenshot.jpg)

As well as the most recently recorded data the webpages plot historic weather data for both the past 24 hours rainfall and also the last 7 days of temperature, humidity, pressure and daily rainfall.
![Screenshot of the web interface plotting historiic  weather data including current temperature, humidity, pressure and more.](https://github.com/sdmeers/weatherstation/blob/main/weatherstation-graphs.jpg)


## Installation


=== MySQL Create Table Command === 

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


ALTER TABLE data MODIFY COLUMN luminance DOUBLE(7,2) NOT NULL;
ALTER TABLE data MODIFY COLUMN humidity DOUBLE(4,1) NOT NULL;
ALTER TABLE data MODIFY COLUMN rain_rate DOUBLE(6,5) NOT NULL;

## Running weather_app.py as a service in Linux

- Created service file /home/sdmeers/OneDrive/Steve/Code/weatherstation/weather_app.service
- Saved to /etc/systemd/system/weather_app.service
- Reload the System Daemon: After creating the service file, reload the systemd daemon to recognize your new service:
	- sudo systemctl daemon-reload
- Enable the Service: This will set your service to start on boot:
	- sudo systemctl enable weather_app.service
- Start the Service: To start the service immediately without rebooting:
	- sudo systemctl start weather_app.service
- To check the status of your service:
	- sudo systemctl status weather_app.service
- Stop, restart & disable your service:
	- sudo systemctl stop weather_app.service
	- sudo systemctl restart weather_app.service
	- sudo systemctl disable weather_app.service
- View Logs via syslog
	- journalctl -n 50 -u weather_app.service

===Exporting SQL Data to csv ====

SELECT *
FROM data
INTO OUTFILE '/tmp/20240109-weather_data.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';

