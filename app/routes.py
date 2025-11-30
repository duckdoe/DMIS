import os
from flask import Flask, request, jsonify, send_from_directory, url_for
from .db.models import BaseModel, create_documents
from app.upload_route import allowed_file, create_folder, create_patient_folder
from werkzeug.utils import secure_filename
# from app import app
import datetime
import jwt
from .utils.mail import appointment_scheduled, appointment_rejected, appointment_rescheduled
from .utils.otp import authorize_user
from .db.models import  BaseModel, create_appointment
from .utils.rate_limiter import rate_limit
from .utils.hash import hash_password, verify

app = Flask(__name__)
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
        400,
    )

#---- PATIENT ROUTES ----#
@app.post("/patient")
def create_patient():
    body = request.get_json()
    data = BaseModel("patients")

    data.set(
        first_name=body["first_name"],
        last_name=body["last_name"],
        dob=body["dob"],
        gender=body["gender"],
        email=body["email"]
    )

    return {"message": "Patient Registered Successfully"}, 201

@app.get("/patients/<id>") #getting a single patient
def get_patient(id):
    data = BaseModel('patients')

    patient = data.get(id=id)
    if not patient:
        return {"error": "Patient not found"}, 404
    
    return {"Patient Details": patient}, 200

@app.get("/patients") #searching patients with specific keywords
def get_patients():
    search = request.args.get("search")
    data = BaseModel("patients")
    if search:
        return data.search_patients_like(search)
    
    return data.get(all=True)

@app.put("/patients/<id>") #updating a patient
def update_patients(id,first_name=None,last_name=None,dob=None,gender=None, email=None):
    data = BaseModel("patients")
    body = request.get_json()
    
    patient=data.update(
    where={"id": id},
    first_name=body.get("first_name"),
    last_name=body.get("last_name"),
    dob=body.get("dob"),
    gender=body.get("gender"),
    email=body.get("email")
   )

    if not patient:
        return {"error": "Patient not found"}, 404
    
    return {"Patient Updated Successfully": patient}, 200

@app.delete("/patients/<id>") #deleting a patient
def delete_patient(id):
    data = BaseModel("patients")
    
    patient = data.delete(id=id)
    if not patient:
        return {"error": "Patient not found"}, 404
    
    return {"Patient Deleted Successfully": patient}, 200


#---- DOCUMENT ROUTES ----#
@app.post("/patients/<id>/documents") #uploading a patient documents
def upload_document(id):
    file = request.files.get("file")
    
    if not file or file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    create_folder()
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 403

    patient_folder = create_patient_folder(id)

    filename = secure_filename(file.filename)
    file_path = os.path.join(patient_folder, filename)
    file.save(file_path)

    file_url = url_for('uploaded_file', patient_id=id, file_name=filename, _external=True)

    # optional form fields
    uploader_id = request.form.get("uploader_id")  # optional, expect UUID string or None
    document_type = request.form.get("document_type")  # optional
    mime_type = file.mimetype if hasattr(file, "mimetype") else None

    document_id = BaseModel("documents").set(
        patient_id=id,
        uploader_id=uploader_id,
        file_name=filename,
        storage_path=file_path,
        mime_type=mime_type,
        document_type=document_type
    )

    if not document_id:
        return {"error": "Document not uploaded or empty null"}, 500

    return {"Document Uploaded Successfully": {"id": document_id, "url": file_url}}, 200

@app.get("/patients/<id>/documents") #listing all documents of a patient
def list_patient_documents(id: int):
    docs = BaseModel('documents')
    
    # get all documents for this patient
    documents = docs.get(all=True, patient_id=id)
    
    return {
        "message": "Documents for patient",
        "patient_id": id,
        "documents": documents
    }

@app.get('/documents/<patient_id>/download/<file_name>') #to download or preview documents of patients
def uploaded_file(patient_id, file_name):
    patient_folder = os.path.join(app.config['UPLOAD_FOLDER'], patient_id)
    return send_from_directory(patient_folder, file_name)

@app.post("/appointments-requests")
def create_appointments_request():
    token = authorize_user()
    if token is None:
        return jsonify({
            "error": "no bearer token found"
        }),404
    if token is False:
        return jsonify({
            "error": "incorrect or invalid bearer token"
        })
    if token['role'] != 'receptionist':
        return jsonify({
            "error": "unauthorized"
        }),403
    data = request.get_json()
    patient_id = data.get("patient_id")
    doctor_id = data.get("doctor_id")
    preferred_date = data.get("preferred_date")
    reason = data.get("reason")
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
            return {"error": "User not found"}, 404
    return (
                jsonify(
                    {"error": "No doctor found with the corresponding information"}
                ),
                404,
            )

@app.get('/appointments/pending')
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

    visits = visit_model.get(doctor_id=doctor_id)

    return jsonify({
        "visits": visits
    }), 200



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
                "success": "All visits to the hospital has been fetched successfully",
                "visits": visits,
            }
        ),
        200,
    )

