import streamlit as st
import mysql.connector
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import datetime
import pandas as pd
import traceback
from sql_config import config
from weather_helper import get_data, convert_wind_direction

# Database connection is kept for potential future use
def get_db_connection():
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Database connection error: {err}")
        return None

def generate_python_query(llm, question):
    # Create a context with database schema information and examples
    db_schema = """
    Table: data
    Fields:
    - id: INT (auto-increment primary key)
    - timestamp: DATETIME (when the data was recorded)
    - temperature: DOUBLE(4,2) (in Celsius)
    - pressure: DOUBLE(6,2) (in hectopascals/hPa)
    - humidity: DOUBLE(3,1) (in percent %)
    - rain: DOUBLE(6,2) (accumulated rainfall in millimeters)
    - rain_rate: DOUBLE(6,5) (rainfall rate in mm/s)
    - luminance: DOUBLE(7,2) (in lux)
    - wind_speed: DOUBLE(3,1) (in meters per second)
    - wind_direction: DOUBLE(3,0) (in degrees)
    - day: INT(3) (day of year)
    - week: INT(2) (week number)
    - month: INT(2) (month number)
    - year: INT(4) (year)
    
    Data starts from 2023-06-06 and is recorded approximately every 15 minutes.
    """
    
    # Create a prompt template with improved guidance for using get_data
    prompt_template = """
    You are a weather data analyst. Below is a description of a weather database and instructions on how to retrieve and analyze weather data:
    
    {db_schema}
    
    You have a function get_data() to retrieve weather data based on different time ranges:
    - get_data("latest") - gets the most recent record
    - get_data("first") - gets the very first record
    - get_data("today") - gets data for the current day
    - get_data("last24h") - gets data for the last 24 hours
    - get_data("yesterday") - gets data for the previous day
    - get_data("last7days") - gets data for the last 7 days
    - get_data(datetime1, datetime2) - gets data between two datetime objects
    
    Given this information, generate Python code to answer the following question:
    
    User Question: {question}
    
    IMPORTANT GUIDELINES:
    - Use ONLY the get_data() function to retrieve data - DO NOT write SQL queries
    - get_data and datetime have already been defined and are available for use, do NOT try to redefine them
    - there are 30 days in September, April, June, and November
    - there are 31 days in January, March, May, July, August, October, and December
    - February has 28 days, and 29 days in leap years
    - After retrieving the data, use pandas functions to analyze it
    - Always store your final answer in a variable named 'result'
    - Always round numerical results to one decimal place
    - For temperature questions, use the 'temperature' column
    - For pressure questions, use the 'pressure' column
    - For humidity questions, use the 'humidity' column
    - For rain questions, use the 'rain' or 'rain_rate' column as appropriate
    - For wind questions, use the 'wind_speed' and 'wind_direction' columns
    - For "maximum" or "highest" or "warmest" values, use .max() on the appropriate column
    - For "minimum" or "lowest" or "coldest" values, use .min() on the appropriate column
    - For "average" values, use .mean() on the appropriate column

    Example code patterns to follow:
    
    1. For temperature questions:
       ```
       # What was the highest temperature yesterday?
       data = get_data("yesterday")
       max_temp = round(data['temperature'].max(), 1)
       result = max_temp  # Just the numerical value
       ```
    
    2. For rainfall questions:
       ```
       # How much rain did we get last week?
       data = get_data("last7days")
       total_rain = round(data['rain'].sum(), 1)
       result = total_rain  # Just the numerical value
       ```
    
    3. For questions about the weather over specific periods of time:
       ```
       # What was the average temperature in January?
        jan_start = datetime.datetime(2025, 1, 1)
        jan_end = datetime.datetime(2025, 2, 1)
       
        data = get_data(jan_start, jan_end)
        avg_temp = round(data['temperature'].mean(), 1)
       ```
    
    4. For specific month and year combinations (example only, change month and year as needed): 
       ``` 
        Which month was warmer, January 2025 or February 2025?
        
        Create datetime objects for the month ranges
            jan_start = datetime.datetime(2025, 1, 1)
            jan_end = datetime.datetime(2025, 2, 1)
            feb_start = datetime.datetime(2025, 2, 1)
            feb_end = datetime.datetime(2025, 3, 1)

        Get data for specific date ranges
            jan_data = get_data(jan_start, jan_end)
            feb_data = get_data(feb_start, feb_end)
            avg_temp_jan = round(jan_data['temperature'].mean(), 1)
            avg_temp_feb = round(feb_data['temperature'].mean(), 1)

        if avg_temp_jan > avg_temp_feb:
            warmer_month = "January"
        else:
            warmer_month = "February"

        result = {{"warmer_month": warmer_month, "january_temp": avg_temp_jan, "february_temp": avg_temp_feb}}
        ```
    
    5. For specific month and year combinations (example only, change month and year as needed): 
       ``` 
        Which month was colder, September 2025 or October 2025?
        
        Create datetime objects for the month ranges
            sept_start = datetime.datetime(2025, 9, 1)
            sept_end = datetime.datetime(2025, 10, 1)
            oct_start = datetime.datetime(2025, 10, 1)
            oct_end = datetime.datetime(2025, 11, 1)

        Get data for specific date ranges
            sept_data = get_data(sept_start, sept_end)
            oct_data = get_data(oct_start, oct_end)
            avg_temp_sept = round(sept_data['temperature'].mean(), 1)
            avg_temp_oct = round(oct_data['temperature'].mean(), 1)

        if avg_temp_sept > avg_temp_oct:
            colder_month = "October"
        else:
            colder_month = "September"

        result = {{"colder_month": colder_month, "sept_temp": avg_temp_sept, "oct_temp": avg_temp_oct}}
        ```
    
    6. For questions about today's weather:

        What was the warmest temperature today?

        data = get_data("today")
        max_temp = round(data['temperature'].max(), 1)
        result = max_temp  # Just the numerical value

    IMPORTANT: ONLY provide valid Python code. DO NOT include any explanations, apologies, markdown code blocks, or natural language. Your response MUST start immediately with Python code that assigns the final result to the variable 'result'.

    """
    
    try:
        # Format the prompt with the input values
        prompt = prompt_template.format(db_schema=db_schema, question=question)
        
        # Generate Python code for data retrieval and analysis
        response = llm.invoke(prompt)
        
        # Clean up the response to get just the Python code
        python_code = response.strip()
        
        # Remove any markdown code block indicators
        python_code = python_code.replace('```python', '').replace('```', '').strip()
        
        # Log the generated code for debugging
        print(f"Generated Python code: {python_code}")
        
        return python_code
    except Exception as e:
        print(f"Error generating Python code: {e}")
        print(traceback.format_exc())
        return None

def execute_python_code(code):
    try:
        # Create a local namespace with the required imports and functions
        local_namespace = {
            'get_data': get_data,
            'convert_wind_direction': convert_wind_direction,
            'datetime': datetime,
            'pd': pd
        }
        
        # Execute the code in the local namespace
        exec(code, globals(), local_namespace)
        
        # Extract the result from the local namespace
        if 'result' in local_namespace:
            return local_namespace['result']
        else:
            print("Error: The generated code did not produce a 'result' variable.")
            return None
    except Exception as e:
        print(f"Error executing Python code: {e}")
        print(traceback.format_exc())
        return None

def format_results(llm, question, results):
    # Convert results to a string format
    if results is None:
        return "I couldn't find any data matching your query."
    
    # Format the results as a simple string
    results_str = str(results)
    
    # Create a prompt template
    prompt_template = """
    You are a helpful weather data assistant. Given the following question and data analysis results, provide a natural language response.
    
    User Question: {question}
    
    Analysis Results: {results}
    
    Please format your response in a conversational manner. Include all relevant information from the results.
    Focus on directly answering the question clearly and concisely.
    For numerical values, provide appropriate units:
    - For temperature, use °C
    - For rainfall, use mm
    - For pressure, use hPa
    - For humidity, use %
    - For wind speed, use m/s
    
    Response:
    """
    
    prompt = prompt_template.format(question=question, results=results_str)
    
    try:
        # Generate natural language response
        response = llm.invoke(prompt)
        
        # Clean up the response
        return response.strip()
    except Exception as e:
        print(f"Error formatting results: {e}")
        print(traceback.format_exc())
        return "I found some data, but I'm having trouble interpreting it."

# Main app
def main():
    st.title("Weather Station Chatbot")
    
    # Initialize LLM
    llm = OllamaLLM(model="llama3.1")

    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask about your weather data"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Generating query..."):
                python_code = generate_python_query(llm, prompt)
                if python_code:
                    with st.expander("Debug - Generated Code"):
                        st.code(python_code, language="python")
                else:
                    st.error("Failed to generate Python code")
                
            if python_code:
                with st.spinner("Executing data analysis..."):
                    try:
                        results = execute_python_code(python_code)
                        
                        if results is not None:
                            with st.spinner("Formatting response..."):
                                response = format_results(llm, prompt, results)
                                st.markdown(response)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                        else:
                            st.markdown("I couldn't analyze the data for your query.")
                            st.session_state.messages.append({"role": "assistant", "content": "I couldn't analyze the data for your query."})
                    except Exception as e:
                        st.error(f"Error executing Python code: {e}")
                        st.markdown("I had trouble analyzing the weather data.")
                        st.session_state.messages.append({"role": "assistant", "content": "I had trouble analyzing the weather data."})
            else:
                st.markdown("I'm sorry, I couldn't understand that question.")
                st.session_state.messages.append({"role": "assistant", "content": "I'm sorry, I couldn't understand that question."})

if __name__ == "__main__":
    main()