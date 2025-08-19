import streamlit as st
import requests
import time
import json
import sqlalchemy
import tempfile
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="MetaMind 🧠",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded" # Keep sidebar open initially
)

# --- Initialize Session State ---
if 'generated_docs' not in st.session_state:
    st.session_state.generated_docs = None
if 'schema_context' not in st.session_state:
    st.session_state.schema_context = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''

# --- Sidebar for API Key Input ---
with st.sidebar:
    st.header("Configuration")
    st.markdown("Enter your Groq API key below. You can get a free key from [GroqCloud](https://console.groq.com/keys).")
    
    # Use a password input to hide the key
    user_api_key = st.text_input(
        "Groq API Key:", 
        type="password", 
        placeholder="gsk_...",
        help="Your key is not stored. It is only used for this session."
    )
    
    if user_api_key:
        st.session_state.api_key = user_api_key
        st.success("API Key accepted!", icon="✅")

# --- API Function ---
def call_groq_api(prompt):
    """
    Makes a fetch call to the Groq API using the key from the UI or .env file.
    """
    # --- UPDATED: Prioritize the key entered in the UI ---
    api_key = st.session_state.api_key
    
    # Fallback to .env or secrets if UI key is not provided
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GROQ_API_KEY") 
        except ImportError:
            pass
    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except (KeyError, FileNotFoundError):
            pass

    if not api_key:
        st.error("Groq API Key not found. Please enter it in the sidebar to begin.")
        return None

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "llama3-70b-8192", "messages": [{"role": "user", "content": prompt}]}

    retries = 3
    delay = 1
    for i in range(retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            if result.get('choices') and result['choices'][0].get('message'):
                return result['choices'][0]['message']['content']
            else:
                st.error("Invalid response structure from Groq API.")
                return None
        except requests.exceptions.RequestException as e:
            if i < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                st.error(f"API call failed after multiple retries: {e}")
                return None
    return None

# --- Database Schema Extraction Function ---
def get_schema_from_db_file(uploaded_file):
    schema_string = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    engine = None
    try:
        engine = sqlalchemy.create_engine(f"sqlite:///{tmp_path}")
        inspector = sqlalchemy.inspect(engine)
        table_names = inspector.get_table_names()

        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            schema_string += f"CREATE TABLE {table_name} (\n"
            for i, column in enumerate(columns):
                col_name = column['name']
                col_type = column['type']
                schema_string += f"    {col_name} {col_type}"
                if i < len(columns) - 1:
                    schema_string += ",\n"
            schema_string += "\n);\n\n"
        
        if engine:
            engine.dispose()
        return schema_string
    except Exception as e:
        st.error(f"Error reading database file: {e}")
        if engine:
            engine.dispose()
        return None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# --- UI Layout ---
st.title("MetaMind 🧠")
st.markdown("Instantly generate documentation and chat with your database schema.")
st.markdown("---")

# --- Input Section ---
input_method = st.radio(
    "Choose your input method:",
    ('Upload SQLite File', 'Paste SQL Schema'),
    horizontal=True,
    key='input_method'
)

schema_to_process = None

if input_method == 'Upload SQLite File':
    st.subheader("Upload your SQLite database file (.db, .sqlite)")
    uploaded_file = st.file_uploader("Upload a SQLite database file", type=['db', 'sqlite', 'sqlite3'], label_visibility="collapsed")
    if uploaded_file is not None:
        schema_to_process = get_schema_from_db_file(uploaded_file)
else:
    st.subheader("Paste your SQL `CREATE TABLE` statement(s) below:")
    schema_to_process = st.text_area("SQL Schema Input", placeholder="-- For MySQL, PostgreSQL, etc.\nCREATE TABLE users (...);", height=250, label_visibility="collapsed")

# --- Generate Documentation Button ---
if st.button("Generate Documentation", type="primary", use_container_width=True):
    if not st.session_state.api_key and not os.getenv("GROQ_API_KEY"):
         st.warning("Please enter your Groq API Key in the sidebar before generating documentation.")
    elif schema_to_process and schema_to_process.strip():
        st.session_state.schema_context = schema_to_process
        st.session_state.chat_history = [] 
        
        prompt = f"""
            You are an expert data analyst. Your task is to generate comprehensive documentation for the provided SQL database schema.
            For each table, provide: **Table Purpose**, **Column Descriptions**, **Business Tags**, and **Suggested Data Quality Checks**.
            Analyze the following SQL schema:
            ---
            {schema_to_process}
            ---
        """
        with st.spinner("The AI is documenting your schema..."):
            st.session_state.generated_docs = call_groq_api(prompt)
    else:
        st.warning("Please upload a file or paste a schema to continue.")

# --- Display Documentation and Chat ---
if st.session_state.generated_docs:
    st.markdown("---")
    st.subheader("Generated Documentation")
    st.markdown(st.session_state.generated_docs)
    
    st.markdown("---")
    st.subheader("💬 Chat with Your Schema")

    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)

    if user_question := st.chat_input("Ask a question about your schema..."):
        st.session_state.chat_history.append(("user", user_question))
        with st.chat_message("user"):
            st.markdown(user_question)

        chat_prompt = f"""
            You are an AI assistant answering questions about a database schema. Use ONLY the information below to answer.

            --- SCHEMA CONTEXT ---
            {st.session_state.schema_context}

            --- DOCUMENTATION CONTEXT ---
            {st.session_state.generated_docs}
            
            --- CHAT HISTORY ---
            {st.session_state.chat_history}

            --- USER'S NEW QUESTION ---
            {user_question}
        """
        
        with st.spinner("Thinking..."):
            ai_response = call_groq_api(chat_prompt)
            if ai_response:
                st.session_state.chat_history.append(("assistant", ai_response))
                with st.chat_message("assistant"):
                    st.markdown(ai_response)
            else:
                st.error("Failed to get a response from the AI.")

# --- Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey;'>A project exploring AI in the modern data stack.</p>", unsafe_allow_html=True)
