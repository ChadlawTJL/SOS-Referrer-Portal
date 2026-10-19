import os
#psycopg is needed to connect and use postgresql database 
import psycopg
#this will return the results as a dictornary which should be easier to read
from psycopg.rows import dict_row
from dotenv import load_dotenv

#connects to the env file to look for the connection details

load_dotenv()

def get_db_connection():
    return psycopg.connect(os.getenv("DATABASE_URL"))