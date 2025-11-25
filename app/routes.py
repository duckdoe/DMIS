from app import app
from .Models.models import printHello


@app.route("/")
def index():
    return printHello("Fortune")
