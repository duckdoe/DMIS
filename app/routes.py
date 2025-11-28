# from app import app
from .Utils.mail import appointment_scheduled, appointment_rejected, appointment_rescheduled
from .Utils.otp import authorize_user
from .db.models import  BaseModel, create_appointment
from flask import Flask, request, jsonify

app = Flask(__name__)

# @app.route("/")
# def index():
#     return printHello("Fortune")

@app.post('/appointments-requests')
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
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor_id')
    preferred_date = data.get('preferred_date')
    reason = data.get('reason')

    if not all([patient_id, doctor_id, preferred_date, reason]):
        return jsonify({
            "message": "Please provide all required fields",
        }),400
    users = BaseModel("users")
    identity = users.get(id=id)
    if not identity or identity.role != 'doctor':
        return jsonify({
            "error": "doctor not found",
        }),400
    appt = create_appointment(patient_id, doctor_id, preferred_date, reason)
    return jsonify({"message": "appointment requested","id":appt.id,"status":appt.status}),201

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



