import mysql.connector
from datetime import datetime, timedelta
from dateutil import tz
import numpy as np
import pandas as pd
from sql_config import config

def read_data_from_db(query, params=None):
    '''
    Executes a SQL query against a MySQL database and returns the results.

    Parameters:
        query (str): A string containing the SQL query to be executed.
        params (tuple or dict, optional): Parameters to pass to the SQL query. Defaults to None.

    Returns:
        list of tuples: Raw data fetched from the database.

    Usage Examples:
        # Example 1: Fetching data with a simple query
        query = "SELECT * FROM data LIMIT 5"
        raw_data = read_data_from_db(query)
        data = pd.DataFrame(raw_data, columns=("id", "datetime", "temperature", "pressure", "humidity", "rain", "rain_rate", "luminance", "wind_speed", "wind_direction", "day", "week", "month", "year"))

        # Example 2: Using parameters in the query
        start_date = '2021-01-01'
        end_date = '2021-01-31'
        query = "SELECT * FROM data WHERE Timestamp BETWEEN %s AND %s"
        params = (start_date, end_date)
        raw_data = read_data_from_db(query, params)
        data = pd.DataFrame(raw_data, columns=("id", "datetime", "temperature", "pressure", "humidity", "rain", "rain_rate", "luminance", "wind_speed", "wind_direction", "day", "week", "month", "year"))

    Notes:
        - Ensure that the MySQL database configuration (`host`, `databasename`, `username`, `password`) is correctly set up.
        - The function uses the mysql.connector library to connect to the MySQL database.
        - The returned data needs to be converted into a pandas DataFrame manually.

    Exceptions:
        - Raises mysql.connector.Error if there is an issue with the MySQL connection or query execution.
    '''
    try:
        with mysql.connector.connect(**config) as cnx:
            with cnx.cursor() as cursor:
                cursor.execute(query, params)
                data = cursor.fetchall()
                return data
    except mysql.connector.Error as err:
        print(f"Something went wrong with MySQL connection: {err}")

def get_data(*args):
    """
    Fetches data from a database based on the provided time range criteria.

    Parameters:
        *args : variable length argument list.
            - Can be a single string that defines the time range:
                - "latest": Returns the most recent record.
                - "first": Returns the very first record.
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

    Raises:
        ValueError: If the passed argument(s) don't match any of the expected criteria or if the month number is out of range.

    Usage Examples:
        1. Get the latest data:
           data = get_data("latest")
        2. Get the very first record:
           data = get_data("first")
        3. Get data for January:
           data = get_data("month=1")
        4. Get data for the 50th day of the year:
           data = get_data("day=50")
        5. Get data from Jan 1, 2023 to Jan 31, 2023:
           data = get_data(datetime(2023, 1, 1), datetime(2023, 1, 31))

    Note:
        The function internally uses a helper function 'get_time_range' to compute date ranges based on the argument string.
    
        Inner Function:
            get_time_range(arg: str) -> Tuple[Optional[datetime], Optional[datetime]]:
                - Determines the start and end dates based on a string argument.
                - Used internally by the main function to compute date ranges.
    """
    
    now = datetime.now()

    def get_time_range(arg):
        if arg in ["latest", "first"]:
            return None, None
        elif arg == "today":
            return datetime(now.year, now.month, now.day), datetime(now.year, now.month, now.day) + timedelta(days=1) - timedelta(seconds=1)
        elif "day=" in arg:
            day_num = int(arg.split("=")[1])
            start_date = datetime(now.year, 1, 1) + timedelta(days=day_num-1)
            end_date = start_date + timedelta(days=1)
            return start_date, end_date - timedelta(seconds=1)
        elif arg == "last24h":
            end_date = now
            start_date = end_date - timedelta(days=1)
            return start_date, end_date
        elif arg == "yesterday":
            start_date = datetime(now.year, now.month, now.day) - timedelta(days=1)
            end_date = datetime(now.year, now.month, now.day)
            return start_date, end_date
        elif arg == "week":
            start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)  # Monday of the current week at midnight
            end_date = start_date + timedelta(days=7)  # Sunday at 23:59:59.999999
            return start_date, end_date - timedelta(seconds=1)
        elif "week=" in arg:
            week_num = int(arg.split("=")[1])
            start_date = datetime(now.year, 1, 1) + timedelta(weeks=week_num-1)
            end_date = start_date + timedelta(weeks=1)
            return start_date, end_date - timedelta(seconds=1)
        elif arg == "last7days":
            start_date = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)  # Start of the day seven days ago
            end_date = now
            return start_date, end_date
        elif "month" in arg:
            if "=" in arg:
                # Extract the month number from the argument
                month_num = int(arg.split("=")[1])
                if month_num < 1 or month_num > 12:
                    raise ValueError("Invalid month number")
            else:
                month_num = now.month

            start_date = datetime(now.year, month_num, 1)
            if month_num == 12:
                end_date = datetime(now.year + 1, 1, 1)
            else:
                end_date = datetime(now.year, month_num + 1, 1)
            return start_date, end_date - timedelta(seconds=1)
        elif arg == "year":
            return datetime(now.year, 1, 1), datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
        elif "year=" in arg:
            year_num = int(arg.split("=")[1])
            start_date = datetime(year_num, 1, 1)
            end_date = datetime(year_num+1, 1, 1)
            return start_date, end_date - timedelta(seconds=1)
        elif arg == "all":
            return None, None
        else:
            raise ValueError("Invalid argument")

    if len(args) == 1 and isinstance(args[0], str):
        arg = args[0]
        start_date, end_date = get_time_range(arg)

        if arg == "latest":
            query = "SELECT * FROM data ORDER BY Timestamp DESC LIMIT 1"
        elif arg == "first":
            query = "SELECT * FROM data WHERE id = 1"
        elif arg == "all":
            query = "SELECT * FROM data"
        else:
            query = f"SELECT * FROM data WHERE Timestamp BETWEEN '{start_date}' AND '{end_date}'"
    elif len(args) == 2 and all(isinstance(a, datetime) for a in args):
        start_date, end_date = args
        query = f"SELECT * FROM data WHERE Timestamp BETWEEN '{start_date}' AND '{end_date}'"
    else:
        raise ValueError("Invalid arguments")

    data = pd.DataFrame(read_data_from_db(query), columns=("id", "datetime", "temperature", "pressure", "humidity", "rain", "rain_rate", "luminance", "wind_speed", "wind_direction", "day", "week", "month", "year"))

    return data

def convert_wind_direction(deg):
    '''
    Converts wind direction from degrees to cardinal compass points.

    This function is specifically tailored for the Meersy Weather Station's configuration.
    It maps certain degree values to their corresponding cardinal directions based on the station's installation.

    Parameters:
        deg (int): A single integer representing the measured wind direction in degrees (0-360).

    Returns:
        str: A string representing the converted compass cardinal point (e.g., "N", "NE", "E", etc.).

    Raises:
        ValueError: If the provided degree value does not match any predefined direction.

    Usage:
        try:
            wind_direction_in_degrees = 225
            cardinal_direction = convert_wind_direction(wind_direction_in_degrees)
            print(f"Cardinal Direction: {cardinal_direction}")
        except ValueError as e:
            print(e)

    Note:
        The function currently handles specific degree values (0, 45, 90, 135, 180, 225, 270, 315).
        Other values will cause a ValueError.
    '''
    if deg == 225:
        return "N"
    elif deg == 180:
        return "NW"
    elif deg == 135:
        return "W"
    elif deg == 90:
        return "SW"
    elif deg == 45:
        return "S"
    elif deg == 0:
        return "SE"
    elif deg == 315:
        return "E"
    elif deg == 270:
        return "NE"
    else:
        raise ValueError("Error: Invalid wind direction")