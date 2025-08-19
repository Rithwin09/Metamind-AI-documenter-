import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

# --- 1. SETUP: Load API key and initialize the AI model ---
load_dotenv()
llm = ChatGroq(model="llama3-70b-8192", temperature=0)


# --- 2. DATABASE CONNECTION: Connect to our SQLite file ---
DB_URI = 'sqlite:///sample.db'
engine = create_engine(DB_URI)


def get_table_info(table_name, engine):
    """Fetches schema and sample data for a given table."""
    inspector = inspect(engine)
    
    # Get column information
    columns = inspector.get_columns(table_name)
    schema_info = "Columns:\n"
    for col in columns:
        schema_info += f"- {col['name']} ({col['type']})\n"
        
    # Get a few sample rows using Pandas
    try:
        sample_data_df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 3", engine)
        sample_data_info = f"\nSample Data:\n{sample_data_df.to_string()}"
    except Exception as e:
        sample_data_info = f"\nCould not fetch sample data: {e}"
        
    return schema_info + sample_data_info


# --- 3. PROMPT ENGINEERING: The instructions for our AI ---
# ⭐⭐⭐ THIS IS THE UPGRADED SECTION ⭐⭐⭐
prompt_template = ChatPromptTemplate.from_messages([
    ("system", 
     "You are an expert data analyst and data quality specialist. Your task is to generate comprehensive documentation for database tables. "
     "Based on the table's schema and sample data, provide the following in Markdown format:\n"
     "1. A brief, one-sentence description of the table's purpose.\n"
     "2. A bulleted list of descriptions for each column.\n"
     "3. A list of 3-5 relevant business tags (e.g., 'Finance', 'User Data').\n"
     "4. A new section called 'Suggested Data Quality Checks' with a bulleted list of 2-3 specific, actionable rules. For example, suggest uniqueness for ID columns, format checks for emails or dates, and range checks for amounts."
    ),
    ("human", 
     "Here is the information for the table named '{table_name}':\n\n"
     "{table_info}"
    )
])


# --- 4. LANGCHAIN: Chain the components together ---
chain = prompt_template | llm | StrOutputParser()


# --- 5. EXECUTION: Run the process ---
def main():
    """Main function to run the documentation generator."""
    print("🧠 Starting MetaMind v2 - Now with Quality Checks!\n")
    
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    if not table_names:
        print("No tables found in the database.")
        return

    print(f"Found tables: {', '.join(table_names)}\n")
    
    # Loop through each table and generate documentation
    for table in table_names:
        print(f"--- Generating Documentation for table: {table} ---")
        table_info = get_table_info(table, engine)
        
        # Run the chain with our table info
        response = chain.invoke({
            "table_name": table,
            "table_info": table_info
        })
        
        print(response)
        print("--------------------------------------------------\n")

if __name__ == "__main__":
    main()