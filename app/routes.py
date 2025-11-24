from app import app
from .db.models import printHello


@app.route("/")
def index():
    return printHello("Fortune")
