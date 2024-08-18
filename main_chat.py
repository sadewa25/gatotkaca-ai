import streamlit as st
import time
# ipython display data
# sql alchemy
from sqlalchemy import (
    create_engine,
    MetaData,
)
# import llama-index
from llama_index.core import SQLDatabase
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

# Query Time Retrieval for tables for text-to-sql
from llama_index.core.indices.struct_store.sql_query import (
    SQLTableRetrieverQueryEngine,
)
from llama_index.core.objects import (
    SQLTableNodeMapping,
    ObjectIndex,
    SQLTableSchema,
)
from llama_index.core import VectorStoreIndex


# database connections
# Database connection parameters
db_params = {
    'dbname': 'db_weather',
    'user': 'sadewawicak',
    'password': 'postgres',
    'host': 'localhost',
    'port': '5432'
}

# Connect to the PostgreSQL database
# Create the connection string
connection_string = f"postgresql+psycopg2://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}?options=-csearch_path=public"

# Create the SQLAlchemy engine
engine = create_engine(connection_string)
metadata_obj = MetaData()


st.title("Gatotkaca.AI - Chatbot Weather AI in Indonesia")

# configure ollama model
# Settings.llm = Ollama(model="mistral", request_timeout=120.0)
# Settings.llm = Ollama(model="gemma2:2b", request_timeout=120.0)
# Settings.llm = Ollama(model="tinyllama", request_timeout=120.0)
Settings.llm = Ollama(model="qwen2:0.5b", request_timeout=120.0)
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)

# llm = Ollama(model="mistral", request_timeout=60.0)
# llm = Ollama(model="mistral", request_timeout=60.0)

# sql database
sql_database = SQLDatabase(engine, include_tables=["daily_weather_prov_indonesia"])

weather_stats_text = (
    """
    You are an AI trained to analyze weather data for Indonesia. The data is stored in a table called "weather_indonesia" with the following columns and descriptions:

    time: The date of weather data (format: text, ISO8601).
    weather_code: The most severe weather condition on a given day (WMO code, float).
    temperature_2m_max: Maximum daily air temperature at 2 meters above ground (°C, float).
    temperature_2m_min: Minimum daily air temperature at 2 meters above ground (°C, float).
    sunrise: Sun rise times (ISO8601 text).
    sunset: Sun set times (ISO8601 text).
    daylight_duration: Number of seconds of daylight per day (float).
    sunshine_duration: The number of seconds of sunshine per day (float). Sunshine duration is always less than daylight duration.
    wind_speed_10m_max: Maximum wind speed at 10 meters above ground (float, km/h).
    wind_direction_10m_dominant: Dominant wind direction at 10 meters above ground (float, degrees).
    city: Name of the city (text).
    name_weather_code: Explanation from weather code (text).

    Important Note: If you are unsure of the correct answer or the generated SQL query is incorrect, respond with: "I can't answer that."
    """
)

sql_database_ = SQLDatabase(engine)
table_node_mapping = SQLTableNodeMapping(sql_database_)
table_schema_objs = [
    SQLTableSchema(table_name="daily_weather_prov_indonesia", context_str=weather_stats_text)  # modify the tuple to a string
]  # add a SQLTableSchema for each table

obj_index = ObjectIndex.from_objects(
    table_schema_objs,
    table_node_mapping,
    VectorStoreIndex,
)
query_engine = SQLTableRetrieverQueryEngine(
    sql_database_, obj_index.as_retriever(similarity_top_k=1)
)


# Streamed response emulator
def response_generator(info: str, query_engine: SQLTableRetrieverQueryEngine):
    response = query_engine.query(info).response
    for word in response.split():
        yield word + " "
        time.sleep(0.05)


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(prompt, query_engine))

    # Add user message to chat history
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})