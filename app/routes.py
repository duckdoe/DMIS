import datetime
import os

import jwt
from flask import jsonify, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from app import app
from app.upload_route import allowed_file, create_folder, create_patient_folder

from .db.models import BaseModel
from .middleware import authenticate_user
from .utils.checkers import is_valid_date
from .utils.format import format_date, format_time
from .utils.hash import hash_password, verify
from .utils.mail import (
    appointment_scheduled,
    send_email,
    send_patient_email,
)
from .utils.otp import generate_otp, send_otp_mail, verify_otp
from .utils.rate_limiter import rate_limit

SECRET_KEY = os.getenv("SECRET_KEY")


# @app.before_request
# def before_request():
#     # Limits the amounts of requests recieved to a 100
#     return rate_limit(20)


@app.route("/upload/test")
def upload_test():
    if request.form:
        print(request.files)
        return "Works"

    return "Doesn't work"


@app.post("/auth/signup")
def signup():
    if request.is_json:
        data = request.get_json()
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")

        if not all([firstname, lastname, email, password, role]):
            return (
                jsonify({"error": "Missing field in payload"}),
                400,
            )

        users = BaseModel("users")
        user = users.get(email=email)

        if user:
            return jsonify({"error": "User already exists"}), 409

        hashed_password = hash_password(password)
        users.set(
            firstname=firstname,
            lastname=lastname,
            email=email,
            password_hash=hashed_password,
            role=role,
        )

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

        email = data.get("email")
        password = data.get("password")

        if not all([email, password]):
            return jsonify({"error": "Missing field in payload"}), 400

        users = BaseModel("users")

        user = users.get(email=email)

        if not user:
            return jsonify({"error": "User does not exist"}), 404

        hashed_password = user.get("password_hash")
        is_same_password = verify(password, hashed_password)

        if not is_same_password:
            return jsonify({"error": "Incorrect password"}), 400

        payload = {
            "id": user.get("id"),
            "role": user.get("role"),
            "email": user.get("email"),
        }
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


@app.post("/patient/create")
def create_patient():
    if request.is_json:
        data = request.get_json()

        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")

        if not all([firstname, lastname, email]):
            return jsonify({"error": "Missing fields in payload"}), 400

        token = authenticate_user()
        if type(token) is not dict:
            return token

        if token.get("role") != "receptionist":
            return jsonify({"error": "Not authorized to access route"}), 403

        patient_model = BaseModel("patients")
        patient = patient_model.get(email=email)

        if patient:
            return jsonify({"error": "Patient already exists"}), 409

        patient_model.set(
            first_name=firstname,
            last_name=lastname,
            email=email,
        )

        # Send email to patient with login url

        patient = patient_model.get(email=email)
        if not patient:
            return jsonify({"error": "Unable to create patient"}), 500

        login_url = url_for("patient_login", id=patient.get("id"), _external=True)

        email_message = f"""
        You have been registered successfully, here is your link to login and request appointments.\n\n {login_url}\n Do not share this with anyone"""

        send_patient_email(
            email_to=email,
            body=email_message,
        )

        return (
            jsonify({"success": "Patient created successfully", "url": login_url}),
            201,
        )

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        400,
    )


@app.post("/patient/login")
def patient_login():
    if request.is_json:
        id = request.args.get("id")

        data = request.get_json()
        email = data.get("email")

        if not all([id, email]):
            return jsonify({"error": "Missing fields in payload check url?"}), 400

        patient_model = BaseModel("patients")
        patient = patient_model.get(id=id)

        if not patient:
            return jsonify({"error": "Unauthorized"}), 403

        otp = generate_otp(email)
        sent = send_otp_mail(email, otp)
        if not sent:
            return (
                jsonify({"error": "Something went wrong when trying to send email"}),
                500,
            )

        return jsonify({"success": "Otp sent to provided email verify"})

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        400,
    )


@app.post("/patient/verify-otp")
def verify_patient_otp():
    if request.is_json:
        id = request.args.get("id")

        data = request.get_json()
        otp = data.get("otp")

        if not all([id, otp]):
            return jsonify({"error": "Missing fields in payload check url?"}), 400

        patient_model = BaseModel("patients")
        patient = patient_model.get(id=id)

        if not patient:
            return jsonify({"error": "Unauthorized"}), 403

        is_correct = verify_otp(patient.get("email"), otp)
        if not is_correct:
            return jsonify({"error": "Invalid or expired otp provided"}), 400

        token = jwt.encode(
            {"id": patient.get("id"), "email": patient.get("email")},
            SECRET_KEY,
            algorithm="HS256",
        )

        return jsonify({"success": "Otp verification successful", "token": token})

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        400,
    )


@app.get("/patients/<id>")  # getting a single patient
def get_patient(id):
    if request.is_json:
        token = authenticate_user()
        if type(token) is not dict:
            return token

        patient_model = BaseModel("patients")
        patient = patient_model.get(id=id)

        if not patient:
            return jsonify({"error": "Patient not found"}), 404

        return (
            jsonify({"success": "Patient retrieved successfully", "patient": patient}),
            200,
        )
    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        400,
    )


@app.get("/patients")  # searching patients with specific keywords
def get_all_patients():
    token = authenticate_user()
    if type(token) is not dict:
        return token

    role = token.get("role")
    if role != "receptionist":
        return jsonify({"error": "Unauthorized"}), 403

    search = request.args.get("search")
    data = BaseModel("patients")
    if search:
        return data.search_patients_like(search)

    return data.get(all=True)


@app.put("/patients/<id>")  # updating a patient
def update_patients(id):
    if request.is_json:
        token = authenticate_user()

        if type(token) is not dict:
            return token

        role = token.get("role")

        if role != "receptionist":
            return jsonify({"error": "Unauthorized access"}), 403

        data = request.get_json()

        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")

        patient_model = BaseModel("patients")
        patient = patient_model.get(id=id)

        if not patient:
            return jsonify({"error": "Patient not found"}), 404

        complete_fields = []
        for field in [firstname, lastname, email]:
            if not field:
                continue
            complete_fields.append(field)

        patient_model.update(
            where={"id": id},
            first_name=firstname,
            last_name=lastname,
            email=email,
        )
        return {"Patient Updated Successfully": patient}, 200

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        400,
    )


@app.delete("/patients/<id>")  # deleting a patient
def delete_patient(id):
    data = BaseModel("patients")

    patient = data.delete(id=id)
    if not patient:
        return {"error": "Patient not found"}, 404

    return {"Patient Deleted Successfully": patient}, 200


# ---- DOCUMENT ROUTES ----#
@app.post("/patients/<id>/documents")  # uploading a patient documents
def upload_document(id):
    token = authenticate_user()

    if type(token) is not dict:
        return token

    role = token.get("role")
    if role != "receptionist":
        return jsonify({"error": "Unauthorized"}), 403

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

    file_url = url_for(
        "uploaded_file", patient_id=id, file_name=filename, _external=True
    )

    # optional form fields
    uploader_id = token.get("id")  # optional, expect UUID string or None
    document_type = request.form.get("document_type")  # optional
    mime_type = file.mimetype if hasattr(file, "mimetype") else None

    document_id = BaseModel("documents").set(
        patient_id=id,
        uploader_id=uploader_id,
        file_name=filename,
        storage_path=file_url,
        mime_type=mime_type,
        document_type=document_type,
    )

    if not document_id:
        return {"error": "Document not uploaded or empty null"}, 500

    return {"Document Uploaded Successfully": {"id": document_id, "url": file_url}}, 200


@app.get("/patients/<id>/documents")  # listing all documents of a patient
def list_patient_documents(id):
    docs = BaseModel("documents")

    # get all documents for this patient
    documents = docs.get(all=True, patient_id=id)

    return {
        "message": "Documents for patient",
        "patient_id": id,
        "documents": documents,
    }


@app.get(
    "/documents/<patient_id>/download/<file_name>"
)  # to download or preview documents of patients
def uploaded_file(patient_id, file_name):
    token = authenticate_user()
    if type(token) is not dict:
        return token

    role = token.get("role")
    if role != "receptionist" or role != "doctor":
        return jsonify({"error": "Unauthorized"}), 403

    upload_folder = app.config["UPLOAD_FOLDER"]

    patient_folder = os.path.join(upload_folder, patient_id)
    return send_from_directory(patient_folder, file_name)


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

    if request.is_json:
        token = (
            authenticate_user()
        )  # Checks whether the user is logged into our system.

        # Checks whether the authenticat_user() function returns something if so it becomes the response

        if type(token) is not dict:
            return token

        data = request.get_json()
        doctor_name = data.get("doctor_name")
        preferred_date = data.get("preferred_date")
        reason = data.get("reason")

        if not all([doctor_name, preferred_date, reason]):
            return (jsonify({"error": "Missing fields in payload"}), 400)

        # Checks if the time provided is a valid date and not a random string
        preferred_date = is_valid_date(preferred_date)
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
            or preferred_date <= current_date + datetime.timedelta(minutes=60)
        ):
            return (
                jsonify(
                    {"error": "Pick a preferred date that is atleast an hour from now"}
                ),
                400,
            )

        # Check if the person accessing the route is a patient
        patient_id = token.get("id")

        patient_model = BaseModel("patients")
        patient = patient_model.get(id=patient_id)

        if not patient:
            return jsonify({"error": "Unauthorized"}), 403

        # Checks whether the doctor exisits
        doctor_model = BaseModel("users")
        doctor = doctor_model.get(firstname=doctor_name, role="doctor")

        if not doctor:
            return (
                jsonify({"error": "User is either not a doctor or does not exist"}),
                404,
            )

        doctor_id = doctor.get("id")

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

        return jsonify({"success": "Appointment created sucessfully"}), 201

    return (
        jsonify(
            {
                "error": "Incomplete or malformed data recieved, try sending in a json payload instead?"
            }
        ),
        500,
    )


@app.get("/appointments/<id>/pending")
def pending_appointments(id):
    """
    This route lists all the pending appointments
    """

    token = authenticate_user()

    # Checks whether the authenticat_user() function returns a valid response
    if type(token) is not dict:
        return token

    doctor_id = token.get("id")
    appointment_model = BaseModel("appointments")

    if id != doctor_id:
        return jsonify({"error": "Invalid id given"})

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

        if type(token) is not dict:
            return token

        data = request.get_json()
        status = data.get("status")

        if status.upper() != "APPROVED":
            return jsonify({"error": "Invalid status provided, try 'approved'?"}), 400

        appointments_model = BaseModel("appointments")

        doctor_id = token.get("id")
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

        appointment_date = appointment.get("preferred_date").strftime("%d/%m/%Y")
        appointment_time = appointment.get("preferred_date").strftime("%H:%M:%S")

        doctor_model = BaseModel("users")
        doctor = doctor_model.get(id=doctor_id, role="doctor")

        if not doctor:
            return jsonify({"error": "Doctor not found"})

        # Format the doctors name
        doctor_name = f"{doctor.get('firstname')} {doctor.get('lastname')}"

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
                    "message": "Appointment approved and email sent successfully",
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

        if type(token) is not dict:
            return token

        role = token.get("role")

        if role != "doctor":
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json()

        reason = data.get("reason")

        if not reason:
            return (
                jsonify(
                    {
                        "error": "Need reason for rejection warning, whatever your reason is will be sent as an email to the patient"
                    }
                ),
                400,
            )

        doctor_id = token.get("id")
        appointments_model = BaseModel("appointments")
        patient_model = BaseModel("patients")

        appointments = appointments_model.get(id=id)  # Fetches an appointment

        # Checks if the appointment being rejected exists
        if not appointments:
            return jsonify({"error": "appointment not found"}), 404

        if appointments.get("doctor_id") != doctor_id:
            return (
                jsonify(
                    {
                        "error": "Doctor trying to access this route is not the one appointed to said patient"
                    }
                ),
                403,
            )

        if appointments.get("status") != "PENDING":
            return (
                jsonify(
                    {
                        "error": "Appointment has either already been approved or rejected to continue you will need an otp"
                    }
                ),
                400,
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

        appointment_date = appointments.get("preferred_date").strftime("%d/%m/%Y")
        appointment_time = appointments.get("preferred_date").strftime("%H:%M:%S")

        doctor_model = BaseModel("users")
        doctor = doctor_model.get(id=doctor_id)

        if not doctor:
            return jsonify({"error": "Doctor not found"})

        name = f"Dr. {doctor.get('firstname')} {doctor.get('lastname')}"

        if not patient.get("email"):
            return (
                jsonify(
                    {
                        "error": "Error sending email, patient does not have a valid email"
                    }
                ),
                500,
            )

        # The email and all of the information concerning it
        subject = "Appointment rejection"
        email_message = f"""
                            Hello {patient.get("firstname")} {patient.get("lastname")}\n 
                            Your appointment with {name} made at{appointment_date} {appointment_time} has been rejected for the following reason.\n\n
                            '{reason}'.\n\n

                            Please consider rescheduling with the same doctor or a different doctor.\nThank you for your understanding.
                        """

        sent = send_email(patient.get("email"), email_message, subject)  # Sends email.

        # Checks whether or not the email was sent successfully.
        if not sent:
            return jsonify({"Error during sending of email try again"}), 500

        # Update of said appointment
        appointments_model.update(
            status="REJECTED", where={"id": id, "doctor_id": doctor_id}
        )

        return (
            jsonify(
                {
                    "message": "Appointment rejected email sent successfully",
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


@app.patch("/appointment/<id>/reschedule")
def reschedule_appointment(id):
    if request.is_json:
        token = authenticate_user()

        if type(token) is not dict:
            return token

        role = token.get("role")
        if role != "doctor":
            return jsonify({"error": "Unauthorized"}), 403

        doctor_id = token.get("id")
        appointment_model = BaseModel("appointments")

        appointment = appointment_model.get(id=id)

        if not appointment:
            return jsonify({"error": "Appointment not found"}), 404

        if appointment.get("doctor_id") != doctor_id:
            return (
                jsonify(
                    {
                        "error": "Doctor trying to rescheduling this appointment is not the same as the one requested for the appointment"
                    }
                ),
                409,
            )

        if appointment.get("status") != "PENDING":
            return jsonify(
                {
                    "error": "Appointment has either been rejected, approved or rescheduled"
                }
            )

        data = request.get_json()
        new_time = data.get("preferred_date")

        if not new_time:
            return jsonify({"error": "New rescheduled date was not recieved"}), 400

        if not is_valid_date(new_time):
            return (
                jsonify(
                    {
                        "error": "This date provided is not a vaild date consider re-formatting the date"
                    }
                ),
                400,
            )

        old_time = appointment.get("preferred_date")
        new_time = is_valid_date(new_time)

        print(type(old_time), type(new_time))

        if new_time == old_time or new_time < old_time:
            return jsonify(
                {
                    "error": "The new time for the appointment must be greater than the old time"
                }
            )
        if new_time <= old_time + datetime.timedelta(minutes=60):
            return (
                jsonify(
                    {"error": "Pick a preferred date that is atleast an hour from now"}
                ),
                400,
            )

        time_limit = new_time + datetime.timedelta(minutes=60)

        time_check = appointment_model.get(
            preferred_date=time_limit, doctor_id=doctor_id
        )
        if time_check:
            return (
                jsonify(
                    {
                        "error": "The time being rescheduled to must have atleast a 1 hour gap between other appointments"
                    }
                ),
                409,
            )

        # Send Email
        patient_id = appointment.get("patient_id")

        patient_model = BaseModel("patients")
        patient = patient_model.get(id=patient_id)

        if not patient:
            return (
                jsonify(
                    {
                        "error": "Patient for said appointment does not exist or was not found"
                    }
                ),
                404,
            )

        # Send Email
        doctor_model = BaseModel("users")

        doctor = doctor_model.get(id=doctor_id)
        name = f"Dr. {doctor.get('firstname')} {doctor.get('lastname')}"

        old_date = old_time.strftime("%d/%m/%Y")
        old_time = old_time.strftime("%H:%M:%S")

        new_date_format = new_time.strftime("%d/%m/%Y")
        new_time_format = new_time.strftime("%H:%M:%S")

        # Send Email to patient
        patient_email = patient.get("email")
        subject = "Appointment Rescheduling"
        email_message = f"""
            Your appointment with {name} has been rescheduled from {old_date} {old_time} to {new_date_format} {new_time_format}\n
            Thank you.
        """

        sent = send_email(patient_email, email_message, subject)
        if not sent:
            return (
                jsonify(
                    {
                        "error": "An error occured while trying to send the email, please try again"
                    }
                ),
                500,
            )

        # Send email to doctor
        doctor_email = doctor.get("email")

        email_message = f"""
                Hello {name} your appointment with {patient.get("firstname")} {patient.get("lastname")} 
                has been rescheduled at {new_date_format} {new_time_format}.\n

                If you have any 
            """
        sent = send_email(doctor_email, email_message, subject)

        # Update appointment
        appointment_model.update(preferred_date=new_time, where={"id": id})

        return (
            jsonify(
                {
                    "message": "Appointment successfully rescheduled and email sent successfully",
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


@app.post("/visits")
def visits():
    token = authenticate_user()

    if type(token) is not dict:
        return token

    role = token.get("role")

    if role != "receptionist":
        return (
            jsonify({"error": "Unauthorized you are not allowed to access this route"}),
            403,
        )

    if not request.is_json:
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
        receptionist_id=id,
        appointment_id=appointment_id,
        notes=notes,
    )

    visit = visits_model.get(appointment_id=appointment_id)
    return jsonify({"success": "Visit successfully recorded", "visit": visit}), 201


@app.get("/visits")
def get_all_visits():
    token = authenticate_user()

    if type(token) is not dict:
        return token

    role = token.get("role")
    if role != "receptionist":
        return jsonify({"error": "Unauthorized"}), 403

    visits_model = BaseModel("visits")
    visits = visits_model.get(all=True)

    return jsonify(
        {"success": "All visits to the hospital successfully fetched", "visits": visits}
    ), 200


@app.get("/visit/<id>")
def get_visits(id):
    token = authenticate_user()

    if type(token) is not dict:
        return token

    role = token.get("role")

    if role != "receptionist":
        return (
            jsonify({"error": "Unauthorized you are not allowed to access this route"}),
            403,
        )

    visit_model = BaseModel("visits")

    visits = visit_model.get(id=id)

    return (
        jsonify(
            {
                "success": "All visits to the hospital has been fetched successfully",
                "visits": visits,
            }
        ),
        200,
    )
