import os
import jwt
import datetime
from flask import request
from flask import jsonify
from app import app
from .db.models import BaseModel
from .db.models import create_appointment
from .utils.hash import hash_password
from .utils.hash import verify
from .utils.checkers import is_valid_date
from .middleware import authenticate_user
from .utils.rate_limiter import rate_limit

SECRET_KEY = os.getenv("SECRET_KEY")


# Does something before a request is processed
@app.before_request
def before_request():
    # Limits the amounts of requests recieved to a 100
    return rate_limit(100)


@app.route("/")
def index():
    return {"message": "Hello"}, 200


@app.post("/auth/signup")
def signup():
    if request.is_json:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
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


@app.post("/auth/login")
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

        hashed_password = user.get("password_hash")
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
    authenticate_user()  # Checks whether the user is logged into our system.

    data = request.get_json()
    patient_id = data.get("patient_id")
    doctor_id = data.get("doctor_id")
    preferred_date = data.get("preferred_date")
    reason = data.get("reason")

    # Checks if the time provided is a valid date and not a random string
    preferred_date = is_valid_date()
    if not preferred_date:
        return (
            jsonify({"error": "Invalid date provided please check your date format"}),
            400,
        )

    current_date = datetime.datetime.now()

    # Checks if the time provided is an hour greater than the current time
    if (
        preferred_date <= current_date
        or preferred_date <= current_date + datetime.timedelta(min=60)
    ):
        return (
            jsonify(
                {"error": "Pick a preferred date that is atleast an hour from now"}
            ),
            400,
        )

    # Checks if the doctor that was requested for an appointment is already booked.
    appointments = BaseModel("appointments")
    appointment = appointments.get(doctor_id=doctor_id, created_at=preferred_date)
    if appointment:
        return (
            jsonify(
                {
                    "error": "This doctor is currently booked for another appointment, try a different time or doctor"
                }
            ),
            409,
        )

    if not all([patient_id, doctor_id, preferred_date, reason]):
        return (jsonify({"message": "Please provide all required fields"}), 400)

    users = BaseModel("users")
    user = users.get(id=id)
    if not user:
        return (
            jsonify({"error": "No doctor found with the corresponding information"}),
            404,
        )

    # Made code more pythonic now returning different messages based on what happened
    role = user.get("role")
    if role != "doctor":
        return jsonify({"error": "This staff is not a doctor"}), 409

    appointments.set(
        patient_id=patient_id,
        doctor_id=doctor_id,
        preferred_date=preferred_date,
        reason=reason,
    )
    new_appointment = appointments.get(
        doctor_id=doctor_id, preferred_date=preferred_date
    )

    if not new_appointment:
        return jsonify(
            {"error": "An error ocurred while trying to create the appointment"}
        )

    return (
        jsonify(
            {
                "success": "Appointment request submitted, awaiting approval",
                "appointment_status": new_appointment.get("status"),
                "appointment_id": new_appointment.get("id"),
            }
        ),
        201,
    )
