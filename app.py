from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import streamlit as st
from langchain_ollama.llms import OllamaLLM

def init_database(user: str, password: str, host: str, port: str, database: str) -> SQLDatabase:
  db_uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
  return SQLDatabase.from_uri(db_uri)

def get_sql_chain(db):
  
  template = """
    Context: You are a weather data analyst with access to a comprehensive weather data database. The database contains historical and real-time weather data, including date, world ,eteorological organization (WMO) code, temp max, temp min, date and time sunrise, 
    date and time sunset, duration sunrise in seconds, duration daylight in seconds, conditions which will explain weather condition based on wmo code, city and more, 
    across various locations and timeframes. You are tasked with explaining and interacting with this database through a question-and-answer format. 
    Your goal is to help users understand how to extract specific insights, trends, and patterns from the weather data. In this database use the schema public.

    Instructions:

    User Interaction: The user will ask specific questions about weather trends, historical data, or forecasts. Your task is to respond with clear, concise, and informative answers using the data available in your database.

    For example, if the user asks, "What was the average temperature in Surabaya City in 28 July 2023?" provide a detailed explanation of how to query this data, and present the result.
    Data Explanation: If the user inquires about how the data is structured or asks for help in forming a query, provide an overview of the database's structure, including key tables, data fields, and common query techniques.

    For example, if asked, "How the conditions in Surabaya at 28 July 2024?" you might present a summary of the data, followed by an analysis of any significant changes or patterns in precipitation.
    Tone: Maintain an informative and accessible tone, ensuring that both technical and non-technical users can understand your explanations.

    End Goal: By the end of the interaction, the user should feel confident in navigating and querying the weather database to answer their own questions or gain insights into weather patterns.
    """
    
  prompt = ChatPromptTemplate.from_template(template)
  
  llm = OllamaLLM(model="mistral", temperature=0)
  
  def get_schema(_):
    return db.get_table_info()
  
  return (
    RunnablePassthrough.assign(schema=get_schema)
    | prompt
    | llm
    | StrOutputParser()
  )
    
def get_response(user_query: str, db: SQLDatabase, chat_history: list):
  
  sql_chain = get_sql_chain(db)

  template = """
    Context: You are a weather data analyst with access to a comprehensive weather data database. The database contains historical and real-time weather data, including date, world ,eteorological organization (WMO) code, temp max, temp min, date and time sunrise, 
    date and time sunset, duration sunrise in seconds, duration daylight in seconds, conditions which will explain weather condition based on wmo code, city and more, 
    across various locations and timeframes. You are tasked with explaining and interacting with this database through a question-and-answer format. 
    Your goal is to help users understand how to extract specific insights, trends, and patterns from the weather data. In this database use the schema public.

    Instructions:

    User Interaction: The user will ask specific questions about weather trends, historical data, or forecasts. Your task is to respond with clear, concise, and informative answers using the data available in your database.

    For example, if the user asks, "What was the average temperature in Surabaya City in 28 July 2023?" provide a detailed explanation of how to query this data, and present the result.
    Data Explanation: If the user inquires about how the data is structured or asks for help in forming a query, provide an overview of the database's structure, including key tables, data fields, and common query techniques.

    For example, if asked, "How the conditions in Surabaya at 28 July 2024?" you might present a summary of the data, followed by an analysis of any significant changes or patterns in precipitation.
    Tone: Maintain an informative and accessible tone, ensuring that both technical and non-technical users can understand your explanations.

    End Goal: By the end of the interaction, the user should feel confident in navigating and querying the weather database to answer their own questions or gain insights into weather patterns.
    
    Conversation History: {chat_history}
    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {response}
  """

  
  prompt = ChatPromptTemplate.from_template(template)
  
  llm = OllamaLLM(model="mistral", temperature=0)
  
  try:
      chain = (
          RunnablePassthrough.assign(query=sql_chain).assign(
              schema=lambda _: db.get_table_info(),
              response=lambda vars: db.run(vars["query"]),
          )
          | prompt
          | llm
          | StrOutputParser()
      )

      # Ensure chat_history is a list of stringss
      chat_history = [str(item) for item in chat_history]

      # Attempt to run the SQL query
      result = chain.invoke({
          "question": user_query,
          "chat_history": chat_history,
      })
      
  except Exception as e:
      # Handle the error (e.g., log it, return a default response, etc.)
      print(f"An error occurred: {e}")
      result = {"error": "An error occurred while processing your request."}

  return result

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Hello! I'm a SQL assistant. Ask me anything about your database."),
    ]

load_dotenv()

st.set_page_config(page_title="Chat with MySQL", page_icon=":speech_balloon:")

st.title("Chat with MySQL")

with st.sidebar:
    st.subheader("Settings")
    st.write("This is a simple chat application using MySQL. Connect to the database and start chatting.")
    
    st.text_input("Host", value="localhost", key="Host")
    st.text_input("Port", value="5432", key="Port")
    st.text_input("User", value="sadewawicak", key="User")
    st.text_input("Password", type="password", value="postgres", key="Password")
    st.text_input("Database", value="db_weather", key="Database")
    
    if st.button("Connect"):
        with st.spinner("Connecting to database..."):
            db = init_database(
                st.session_state["User"],
                st.session_state["Password"],
                st.session_state["Host"],
                st.session_state["Port"],
                st.session_state["Database"]
            )
            st.session_state.db = db
            st.success("Connected to database!")
    
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("Human"):
      st.markdown(user_query)
        
    with st.chat_message("AI"):
      response = get_response(user_query, st.session_state.db, st.session_state.chat_history)
      st.markdown(response)
        
    if isinstance(response, dict) and response.get("error") is not None:
      st.session_state.chat_history.append(response)
    else:
      st.session_state.chat_history.append(AIMessage(content=response))