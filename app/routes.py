import os
import jwt
from flask import request
from flask import jsonify
from app import app
from .db.models import BaseModel
from .db.models import create_appointment
from .utils.hash import hash_password
from .utils.hash import verify

SECRET_KEY = os.getenv("SECRET_KEY")


@app.post("/auth/signup")
def signup():
    if request.is_json():
        data = request.get_json()
        username = data["username"]
        password = data["password"]
        role = data["role"]

        if not all([username, password, role]):
            return (
                jsonify({"error": "Missing field in payload"}),
                400,
            )

        users = BaseModel("users")
        user = users.get(username=username)

        if user:
            return jsonify({"error": "User already exists"}), 409

        hashed_password = hash_password(password)
        users.set(
            username=username,
            password_hash=hashed_password,
            role=data["role"],
        )

        return jsonify({"message": "user signup successful"}), 201

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending a json request"
            }
        ),
        400,
    )


@app.post("/login")
def login():
    if request.is_json:
        data = request.get_json()

        username = data.get("username")
        password = data.get("password")

        if not all([username, password]):
            return jsonify({"error": "Missing field in payload"}), 400

        users = BaseModel("users")

        user = users.get(username=username)

        if not user:
            return jsonify({"error": "User does not exist"}), 404

        hashed_password = user.get("password")
        is_same_password = verify(password, hashed_password)

        if not is_same_password:
            return jsonify({"error": "Incorrect password"}), 400

        payload = {"username": user.get("username"), "role": user.get("role")}
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({"message": "Login successful", "token": token}), 200

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        400,
    )


@app.post("/appointments-requests")
def create_appointments_request():
    bearer = request.headers.get("Authorization")

    if not bearer:
        return jsonify({"error": "Missing Auth token"}), 400

    token = None
    if not bearer.startswith("Bearer"):
        return jsonify({"error": "No bearer token found"}), 400

    token = bearer.split(" ")

    if token is None:
        return jsonify({"error": "no bearer token found"}), 404
    if token is False:
        return jsonify({"error": "incorrect or invalid bearer token"})

    data = request.get_json()
    patient_id = data.get("patient_id")
    doctor_id = data.get("doctor_id")
    preferred_date = data.get("preferred_date")
    reason = data.get("reason")

    if not all([patient_id, doctor_id, preferred_date, reason]):
        return (
            jsonify(
                {
                    "message": "Please provide all required fields",
                }
            ),
            400,
        )
    users = BaseModel("users")
    identity = users.get(id=id)
    if not identity or identity.role != "doctor":
        return (
            jsonify(
                {
                    "error": "doctor not found",
                }
            ),
            400,
        )
    appt = create_appointment(patient_id, doctor_id, preferred_date, reason)
    return (
        jsonify(
            {"message": "appointment requested", "id": appt.id, "status": appt.status}
        ),
        201,
    )
