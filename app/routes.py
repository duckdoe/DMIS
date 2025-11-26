# from app import app
from .Utils.otp import authorize_user
from .db.models import  BaseModel, create_appointment
from flask import Flask, request, jsonify

app = Flask(__name__)

# @app.route("/")
# def index():
#     return printHello("Fortune")

@app.post('/appointments-requests')
def create_appointments_request():
    token = authorize_user
    if token is None:
        return jsonify({
            "error": "no bearer token found"
        }),404
    if token is False:
        return jsonify({
            "error": "incorrect or invalid bearer token"
        })

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


