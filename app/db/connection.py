import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_USER = os.getenv("DATABASE_USER")


def db_connection():
    connection = psycopg2.connect(
        dbname=DATABASE_NAME,
        port=DATABASE_PORT,
        host=DATABASE_HOST,
        password=DATABASE_PASSWORD,
        user=DATABASE_USER,
    )

    return connection
