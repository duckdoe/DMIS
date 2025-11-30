"""
This file contains all the routes needed for::

Registration
Login
Appointments
Visits
File uploading
Patients
"""

from .utils.mail import appointment_scheduled
from .utils.mail import appointment_rejected
from .utils.mail import appointment_rescheduled
from .db.models import BaseModel
from flask import request
from flask import jsonify
import os
import jwt
import datetime
from datetime import date
from flask import request
from flask import jsonify
from app import app
from datetime import datetime
from .db.models import BaseModel
from .db.models import create_appointment
from .utils.hash import hash_password
from .utils.hash import verify
from .utils.checkers import is_valid_date
from .middleware import authenticate_user
from .utils.rate_limiter import rate_limit

SECRET_KEY = os.getenv("SECRET_KEY")


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
        role = data.get("role")

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
        users.set(username=username, password_hash=hashed_password, role=role)

        return jsonify({"message": "User signup successful"}), 201

    return (
        jsonify(
            {"error": "Incomplete or malformed data recieved, try sending json payload"}
        ),
        500,
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

        payload = {"id": user.get("id"), "role": user.get("role")}
        token = jwt.encode(
            payload, SECRET_KEY, algorithm="HS256"
        )  # Generate jwt token for user

        return jsonify({"success": "Login successful", "token": token}), 200

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        500,
    )


@app.post("/appointments-requests")
def create_appointments_request():
    """
    Route for creating an appointment request

    Accepts the following data from the ``request_body``

    patient_id

    doctor_id

    preferred_date

    reason
    """

    if request.is_json():
        token = (
            authenticate_user()
        )  # Checks whether the user is logged into our system.

        # Checks whether the authenticat_user() function returns something if so it becomes the response

        if type(token) != dict:
            return token

        data = request.get_json()
        patient_id = data.get("patient_id")
        doctor_id = data.get("doctor_id")
        preferred_date = data.get("preferred_date")
        reason = data.get("reason")

        # Checks if the time provided is a valid date and not a random string
        preferred_date = is_valid_date()
        if not preferred_date:
            return (
                jsonify(
                    {"error": "Invalid date provided please check your date format"}
                ),
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
                        "error": "This doctor is currently booked for another appointment for the time requested, try a different time or doctor"
                    }
                ),
                409,
            )

        if not all([patient_id, doctor_id, preferred_date, reason]):
            return (jsonify({"error": "Missing fields in payload"}), 400)

        users = BaseModel("users")
        user = users.get(id=id)
        if not user:
            return (
                jsonify(
                    {"error": "No doctor found with the corresponding information"}
                ),
                404,
            )

        # Made code more pythonic now returning different messages based on what happened
        role = user.get("role")
        if role != "doctor":
            return jsonify({"error": "This staff is not a doctor"}), 409

        # Creates new appointment for patient
        appointments.set(
            patient_id=patient_id,
            doctor_id=doctor_id,
            preferred_date=preferred_date,
            reason=reason,
        )

        # Gets the new appointment
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

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        500,
    )


@app.get("/appointments/pending")
def pending_appointments():
    """
    This route lists all the pending appointments
    """

    token = authenticate_user()

    # Checks whether the authenticat_user() function returns something if so it becomes the response
    if type(token) != dict:
        return token

    doctor_id = token.get("user_id")
    appointment_model = BaseModel("appointments")

    # Gets all pending appointments and returns them as a response
    appointments = appointment_model.get(doctor_id=doctor_id, status="PENDING")
    return (
        jsonify(
            {
                "success": "All pending apointments recieved",
                "appointments": appointments,
                "status": "pending",
            }
        ),
        200,
    )


@app.patch("/appointments/<id>/approve")
def approve_appointments(id):
    if request.is_json:
        token = authenticate_user()

        if type(token) != dict:
            return token

        data = request.get_json()
        status = data.get("status")

        if status.upper() != "APPROVED":
            return jsonify({"error": "Invalid status provided, try 'approved'?"}), 400

        doctor_id = token.get("user_id")
        appointment = appointments_model.get(id=id)

        # Checks if the appointment being approved exists
        if not appointment:
            return (
                jsonify(
                    {
                        "error": "Appointment not found",
                    }
                ),
                404,
            )

        # Checks if the doctor_id provided matches the one for the appointment
        if appointment.get("doctor_id") != doctor_id:
            return (
                jsonify(
                    {
                        "error": "Doctor trying to approve this appointment is not the owner of the appointment",
                    }
                ),
                403,
            )
        if appointment.get("status") != "PENDING":
            return (
                jsonify(
                    {
                        "error": "Appointment has either been rejected, rescheduled or approved already, try approving another appointment?",
                    }
                ),
                400,
            )

        appointments_model.update(
            status="APPROVED", where={"id": id, "doctor_id": doctor_id}
        )

        appointments_model = BaseModel("appointments")
        patient_model = BaseModel("patients")

        patient_id = appointment.get("patient_id")
        patient = patient_model.get(id=patient_id)

        # Check if the patient exists
        if not patient:
            return (
                jsonify({"error": "Patient for this appointnment was not found"}),
                404,
            )

        patient_email = patient.get("email")

        appointment_date = appointment.get("preferred_date").split("T")[0]
        appointment_time = appointment.get("preferred_date").split("T")[1]

        doctor_model = BaseModel("users")
        doctor = doctor_model.get(id=doctor_id, role="doctor")

        if not doctor:
            return jsonify({"error": "Doctor not found"})

        # Format the doctors name
        doctor_name = f"{doctor.get('first_name')} {doctor.get('last_name')}"

        if not patient_email:
            return jsonify({"error": "Patient's email was not found"}), 404

        # Schedule appointment
        appointment_scheduled(
            patient_email,
            appointment_date,
            appointment_time,
            doctor_name,
        )

        return (
            jsonify(
                {
                    "message": "appointment approved and email sent",
                    "appointment_id": id,
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        500,
    )


@app.patch("/appointments/<id>/reject")
def reject_appointment(id):
    if request.is_json:
        token = authenticate_user()

        if type(token) != dict:
            return token

        doctor_id = token.get("user_id")
        appointments_model = BaseModel("appointments")
        patient_model = BaseModel("patients")

        appointments = appointments_model.get(id=id)  # Fetches an appointment

        # Checks if the appointment being rejected exists
        if not appointments:
            return jsonify({"error": "appointment not found"}), 404

        if appointments.get("doctor_id") != doctor_id:
            return jsonify({"error": "not authorized for this appointment"}), 403
        if appointments.get("status") != "PENDING":
            return jsonify({"error": "appointment not in pending state"}), 400

        # Update of said appointment
        appointments_model.update(
            status="REJECTED", where={"id": id, "doctor_id": doctor_id}
        )

        # Send email update to user telling them their appointment was rejected
        patient = patient_model.get(id=appointments.get("patient_id"))

        if not patient:
            return (
                jsonify(
                    {
                        "error": "Patient who requested for the appointment does not exist"
                    }
                ),
                404,
            )

        patient_email = patient.get("email")
        appointment_date = appointments.get("preferred_date").split("T")[0]
        appointment_time = appointments.get("preferred_date").split("T")[1]

        doctor_model = BaseModel("users")
        doctor_data = doctor_model.get(id=doctor_id)
        if doctor_data:
            doctor_data = doctor_data[0]
            doctor_name = (
                f"{doctor_data.get('first_name')} {doctor_data.get('last_name')}"
            )
        else:
            doctor_name = f"Dr. {doctor_id}"

        if patient_email:
            appointment_rejected(
                patient_email, doctor_name, appointment_date, appointment_time
            )

        return (
            jsonify(
                {"message": "appointment rejected and email sent", "appointment_id": id}
            ),
            200,
        )

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        500,
    )


@app.patch("/appointments/<id>/reschedule")
def reschedule_appointment(id):
    if request.is_json:
        token = authenticate_user()

        if type(token) != dict:
            return token

        doctor_id = token.get("user_id")
        appt_model = BaseModel("appointments")
        patient_model = BaseModel("patients")

        appts = appt_model.get(id=id)
        if not appts:
            return jsonify({"error": "appointment not found"}), 404

        appt = appts[0]
        if appt.get("doctor_id") != doctor_id:
            return jsonify({"error": "not authorized for this appointment"}), 403
        if appt.get("status") != "PENDING":
            return jsonify({"error": "appointment not in pending state"}), 400

        # Get new preferred_date from request
        data = request.get_json()
        new_date_time = data.get("preferred_date")
        if not new_date_time:
            return jsonify({"error": "new preferred_date required"}), 400

        old_date_time = appt.get("preferred_date")

        # Update appointment
        appt_model.update(
            preferred_date=new_date_time, where={"id": id, "doctor_id": doctor_id}
        )

        # Send email
        patient = patient_model.get(id=appt.get("patient_id"))
        if patient:
            patient = patient[0]
            patient_email = patient.get("email")

            old_date, old_time = old_date_time.split("T")
            new_date, new_time = new_date_time.split("T")

            doctor_model = BaseModel("users")
            doctor_data = doctor_model.get(id=doctor_id)
            if doctor_data:
                doctor_data = doctor_data[0]
                doctor_name = (
                    f"{doctor_data.get('first_name')} {doctor_data.get('last_name')}"
                )
            else:
                doctor_name = f"Dr. {doctor_id}"

            if patient_email:
                appointment_rescheduled(
                    patient_email, doctor_name, old_date, old_time, new_date, new_time
                )

        return (
            jsonify(
                {
                    "message": "appointment rescheduled and email sent",
                    "appointment_id": id,
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        500,
    )


@app.route("/visits", methods=["POST", "GET"])
def visits():
    token = authenticate_user()

    if type(token) != dict:
        return token

    role = token.get("role")

    if role != "doctor":
        return (
            jsonify({"error": "Unauthorized you are not allowed to access this route"}),
            403,
        )

    if request.method == "POST":
        if not request.is_json():
            return (
                jsonify(
                    {
                        "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
                    }
                ),
                500,
            )

        data = request.get_json()
        patient_id = data.get("patient_id")
        appointment_id = data.get("appointment_id")
        notes = data.get("notes")

        complete = all([patient_id, appointment_id, notes])
        if not complete:
            return jsonify({"error": "Missing fields in payload"}), 400

        id = token.get("id")

        visits_model = BaseModel("visits")
        visits_model.set(
            patient_id=patient_id,
            doctor_id=id,
            appointment_id=appointment_id,
            notes=notes,
        )

        visit = visits_model.get(appointment_id=appointment_id)
        return jsonify({"success": "Visit successfully recorded", "visit": visit}), 201

    doctor_id = token.get("user_id")
    visit_model = BaseModel("visits")

    visits = visit_model.get(doctor_id=doctor_id, all=True)

    return (
        jsonify(
            {
                "success": "All visits to the hospital has been fetched successfully",
                "visits": visits,
            }
        ),
        200,
    )
