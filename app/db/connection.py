import os

import psycopg2
import redis
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

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
        cursor_factory=RealDictCursor,
    )

    return connection


REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_USERNAME = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

r = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    decode_responses=True,
    username=REDIS_USERNAME,
    password=REDIS_PASSWORD,
)
