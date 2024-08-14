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
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.
    
    <SCHEMA>public</SCHEMA>
    
    Conversation History: {chat_history}
    
    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks and forward slash.
    
    For example:
    Question: how many data in the table?
    SQL Query: SELECT COUNT(wd."_id") FROM weather_data wd;

    Question: what is the conditions weather in date 2024-06-30?
    SQL Query: SELECT wd.conditions FROM weather_data wd where wd."date" = '2024-06-30';
    
    Your turn:
    
    Question: {question}
    SQL Query:
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
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.
    
    <SCHEMA>public</SCHEMA>

    Based on the query results, provide a detailed explanation of the data. Include insights and any notable patterns or anomalies.

    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks and forward slash.
    
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
    st.text_input("Database", value="db_daily_weather", key="Database")
    
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
        
    if response["error"] is not None:
      st.session_state.chat_history.append(response)
    else :
      st.session_state.chat_history.append(AIMessage(content=response))