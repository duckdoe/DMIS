from app import app
from .db.models import printHello


@app.route("/")
def index():
    data = BaseModel('user')

    user = data.get(password="")

    if not user:
        return {"error": "User not found"}, 404
    
    
