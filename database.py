import os
import psycopg
from dotenv import load_dotenv

#connects to the env file to look for the connection details
#psycopg is needed to connect and use postgresql database 
load_dotenv()

def get_db_connection():
    return psycopg.connect(os.getenv("DATABASE_URL"))