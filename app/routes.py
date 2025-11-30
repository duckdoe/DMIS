import os
from flask import Flask, request, jsonify, send_from_directory, url_for
from .db.models import BaseModel, create_documents
from app.upload_route import allowed_file, create_folder, create_patient_folder
from werkzeug.utils import secure_filename

# from app import app
import datetime
import jwt
from .Utils.mail import appointment_scheduled, appointment_rejected, appointment_rescheduled
from .Utils.otp import authorize_user
from .db.models import  BaseModel, create_appointment
from .Utils.rate_limiter import rate_limit
from .Utils.hash import hash_password, verify

app = Flask(__name__)

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
        return {"error": "User not found"}, 404
    return (
            jsonify({"error": "No doctor found with the corresponding information"}),
            404,
        )

@app.get('/appointments/pending')
def pending_appointments():
    token = authorize_user()
    doctor_id = token.get("user_id")
    if token is None:
        return jsonify({
            "error": "no bearer token found"
        }),404
    if token is False:
        return jsonify({
            "error": "incorrect or invalid bearer token"
        })
    if token['role'] != 'doctor':
        return jsonify({
            "error": "unauthorized"
        }),403
    appointment_model = BaseModel("appointments")
    patient_model = BaseModel("patients")

    appt = appointment_model.get(doctor_id=doctor_id,status='PENDING')

    result = []

    for a in appt:
        patient_id = a.get("patient_id")
        patient = patient_model.get(id=patient_id)

        result.append({
            "appointment_id": a.get("id"),
            "preferred_date": a.get("preferred_date"),
            "reason": a.get("reason"),
            "patient":{
                "id": patient.get("id"),
                "first_name": patient.get("first_name"),
                "last_name": patient.get("last_name"),
                "email": patient.get("email")
            }

        })

        return jsonify({"pending_appointments":result})

@app.patch('/appointments/<id>/approve')
def approved_appointments(id):
    token = authorize_user()
    doctor_id = token.get("user_id")
    if token is None:
        return jsonify({
            "error": "no bearer token found"
        }),404
    if token is False:
        return jsonify({
            "error": "incorrect or invalid bearer token"
        })
    if token['role'] != 'doctor':
        return jsonify({
            "error": "unauthorized"
        }),403
    appt_model = BaseModel("appointments")
    patient_model = BaseModel("patients")
    appts = appt_model.get(id=id)
    if not appts:
        return jsonify({
            "error": "appointment not found",
        }),404
    appt = appts[0]
    if appt.get("doctor_id") != doctor_id:
        return jsonify({
            "error": "not authorized for this appointment",
        }),403
    if appt.get("status") != 'PENDING':
        return jsonify({
            "error": "appointment not in pending state",
        }),400
    data = request.get_json()
    status = data.get('status')
    if status == 'APPROVED':
        appt_model.update(status="APPROVED",where = {"id": id, "doctor_id": doctor_id})

        patient_id = appt.get("patient_id")
        patient = patient_model.get(id=patient_id)
        if patient:
            patient = patient[0]
            patient_email = patient.get("email")
            patient_name = patient.get("first_name")

            appointment_date = appt.get("preferred_date").split("T")[0]
            appointment_time = appt.get("preferred_date").split("T")[1]

            doctor_model= BaseModel("users")
            doctor_data = doctor_model.get(id=doctor_id)
            if doctor_data:
                doctor_data = doctor_data[0]
                doctor_name = f"{doctor_data.get('first_name')} {doctor_data.get('last_name')}"
            else:
                doctor_name = f"Dr. {doctor_id}"

            if patient_email:
                appointment_scheduled(patient_email, appointment_date, appointment_time, doctor_name)

        return jsonify({"message": "appointment approved and email sent", "appointment_id": id}), 200

    return jsonify({"error": "invalid status"}), 400

@app.patch('/appointments/<id>/reject')
def reject_appointment(id):
    token = authorize_user()
    if token is None:
        return jsonify({"error": "no bearer token found"}), 404
    if token is False:
        return jsonify({"error": "incorrect or invalid bearer token"}), 401
    if token['role'] != 'doctor':
        return jsonify({"error": "unauthorized"}), 403

    doctor_id = token.get("user_id")
    appt_model = BaseModel("appointments")
    patient_model = BaseModel("patients")

    appts = appt_model.get(id=id)
    if not appts:
        return jsonify({"error": "appointment not found"}), 404

    appt = appts[0]
    if appt.get("doctor_id") != doctor_id:
        return jsonify({"error": "not authorized for this appointment"}), 403
    if appt.get('status') != 'PENDING':
        return jsonify({"error": "appointment not in pending state"}), 400

    # Update status
    appt_model.update(status="REJECTED", where={"id": id, "doctor_id": doctor_id})

    # Send email
    patient = patient_model.get(id=appt.get("patient_id"))
    if patient:
        patient = patient[0]
        patient_email = patient.get("email")
        appointment_date = appt.get("preferred_date").split("T")[0]
        appointment_time = appt.get("preferred_date").split("T")[1]

        doctor_model = BaseModel("users")
        doctor_data = doctor_model.get(id=doctor_id)
        if doctor_data:
            doctor_data = doctor_data[0]
            doctor_name = f"{doctor_data.get('first_name')} {doctor_data.get('last_name')}"
        else:
            doctor_name = f"Dr. {doctor_id}"

        if patient_email:
            appointment_rejected(patient_email, doctor_name, appointment_date, appointment_time)

    return jsonify({"message": "appointment rejected and email sent", "appointment_id": id}), 200

@app.patch('/appointments/<id>/reschedule')
def reschedule_appointment(id):
    token = authorize_user()
    if token is None:
        return jsonify({"error": "no bearer token found"}), 404
    if token is False:
        return jsonify({"error": "incorrect or invalid bearer token"}), 401
    if token['role'] != 'doctor':
        return jsonify({"error": "unauthorized"}), 403

    doctor_id = token.get("user_id")
    appt_model = BaseModel("appointments")
    patient_model = BaseModel("patients")

    appts = appt_model.get(id=id)
    if not appts:
        return jsonify({"error": "appointment not found"}), 404

    appt = appts[0]
    if appt.get("doctor_id") != doctor_id:
        return jsonify({"error": "not authorized for this appointment"}), 403
    if appt.get('status') != 'PENDING':
        return jsonify({"error": "appointment not in pending state"}), 400

    # Get new preferred_date from request
    data = request.get_json()
    new_date_time = data.get('preferred_date')
    if not new_date_time:
        return jsonify({"error": "new preferred_date required"}), 400

    old_date_time = appt.get("preferred_date")

    # Update appointment
    appt_model.update(preferred_date=new_date_time, where={"id": id, "doctor_id": doctor_id})

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
            doctor_name = f"{doctor_data.get('first_name')} {doctor_data.get('last_name')}"
        else:
            doctor_name = f"Dr. {doctor_id}"

        if patient_email:
            appointment_rescheduled(patient_email, doctor_name, old_date, old_time, new_date, new_time)

    return jsonify({"message": "appointment rescheduled and email sent", "appointment_id": id}), 200


@app.post('/visits')
def create_visits():
    token = authorize_user()
    doctor_id = token.get("user_id")
    if token is None:
        return jsonify({
            "error": "no bearer token found"
        }),404
    if token is False:
        return jsonify({
            "error": "incorrect or invalid bearer token"
        })
    if token['role'] != 'doctor':
        return jsonify({
            "error": "unauthorized"
        }),403

    data = request.get_json()
    patient_id = data.get("patient_id")
    appointment_id = data.get("appointment_id")
    notes = data.get("notes")

    if not patient_id or not notes:
        return jsonify({"error": "patient_id and notes required"}), 400

    doctor_id = token.get("user_id")
    visit_model = BaseModel("visits")
    visit = visit_model.set(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        notes=notes
    )

    return jsonify({
        "message": "visit created successfully",
        "visit": visit
    }), 201


@app.get('/visits')
def view_visits():
    token = authorize_user()
    if not token or token.get("role") != "doctor":
        return jsonify({"error": "unauthorized"}), 403

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
                "success": "Appointment request submitted, awaiting approval",
                "appointment_status": new_appointment.get("status"),
                "appointment_id": new_appointment.get("id"),
            }
        ),
        201,
    )
