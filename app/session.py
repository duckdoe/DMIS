from dotenv import load_dotenv
import redis
import os

load_dotenv()

HOST = os.getenv("REDIS_HOST")
PORT = os.getenv("REDIS_PORT")
USERNAME = os.getenv("REDIS_USERNAME")
PASSWORD = os.getenv("REDIS_PASSWORD")

r = redis.Redis(
    host=HOST,
    port=int(PORT),
    decode_responses=True,
    username=USERNAME,
    password=PASSWORD,
)
