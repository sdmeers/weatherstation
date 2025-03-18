import streamlit as st
import mysql.connector
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import datetime
from sql_config import config

# Database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Database connection error: {err}")
        return None

# Execute SQL query
def execute_query(query):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except mysql.connector.Error as err:
            st.error(f"Query execution error: {err}")
            return None
    return None

def generate_sql(llm, question):
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
    
    Example queries:
    1. To find the highest temperature yesterday:
       SELECT MAX(temperature) as max_temp, DATE(timestamp) as date 
       FROM data 
       WHERE DATE(timestamp) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
       GROUP BY DATE(timestamp);
    
    2. To find the total rainfall in March 2024:
       SELECT SUM(rain) as total_rain 
       FROM data 
       WHERE year = 2024 AND month = 3;
    
    3. To compare average temperatures between two months:
       SELECT year, month, AVG(temperature) as avg_temp 
       FROM data 
       WHERE (year = 2023 AND month = 7) OR (year = 2024 AND month = 7) 
       GROUP BY year, month;
    """
    
    # Create a prompt template with improved guidance
    prompt_template = """
    You are a weather database expert. Below is a description of a weather database table and example queries:
    
    {db_schema}
    
    Given this schema, generate a valid SQL query to answer the following question:
    
    User Question: {question}
    
    IMPORTANT GUIDELINES:
    - For maximum/minimum values, use MAX() or MIN() functions
    - For time periods like "yesterday", use DATE_SUB(CURDATE(), INTERVAL 1 DAY)
    - For "this month", use YEAR(CURDATE()) and MONTH(CURDATE())
    - Always GROUP BY date fields when performing aggregations over time periods
    - Return only the data needed to answer the question
    - Never use "*" in SELECT statements
    
    Return ONLY the raw SQL query without any markdown formatting, code blocks, backticks, or explanations.
    """
    
    prompt = prompt_template.format(db_schema=db_schema, question=question)
    
    try:
        # Generate SQL query
        response = llm.invoke(prompt)
        
        # Clean up the response to get just the SQL query
        sql_query = response.strip()
        
        # Remove any markdown code block indicators
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
        # Remove any comment lines (which might start with --)
        sql_query = '\n'.join([line for line in sql_query.split('\n') if not line.strip().startswith('--')])
        
        # Log the generated SQL for debugging
        print(f"Generated SQL: {sql_query}")
        
        return sql_query
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return None

def format_results(llm, question, results):
    # Convert results to a string format
    if not results:
        return "I couldn't find any data matching your query."
    
    # Format the results as a simple string
    results_str = str(results)
    
    # Create a prompt template
    prompt_template = """
    You are a helpful weather data assistant. Given the following question and raw database results, provide a natural language response.
    
    User Question: {question}
    
    Database Results: {results}
    
    Please format your response in a conversational manner. Include all relevant information from the database results.
    Focus on directly answering the question clearly and concisely.
    If the results contain dates or times, format them in a human-readable way.
    For numerical values, provide appropriate units (e.g., °C for temperature, mm for rainfall).
    
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
            with st.spinner("Generating SQL..."):
                sql_query = generate_sql(llm, prompt)
                
            if sql_query:
                with st.spinner("Querying database..."):
                    try:
                        results = execute_query(sql_query)
                        
                        if results:
                            with st.spinner("Formatting response..."):
                                response = format_results(llm, prompt, results)
                                st.markdown(response)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                        else:
                            st.markdown("I couldn't find any data matching your query.")
                            st.session_state.messages.append({"role": "assistant", "content": "I couldn't find any data matching your query."})
                    except Exception as e:
                        st.error(f"Error executing query: {e}")
                        st.markdown("I had trouble running the database query.")
                        st.session_state.messages.append({"role": "assistant", "content": "I had trouble running the database query."})
            else:
                st.markdown("I'm sorry, I couldn't understand that question.")
                st.session_state.messages.append({"role": "assistant", "content": "I'm sorry, I couldn't understand that question."})

if __name__ == "__main__":
    main()