import os
from flask import Flask, request, jsonify, send_from_directory, url_for
from ..db.models import BaseModel, create_documents
from route.upload_route import allowed_file, create_folder, create_patient_folder
from werkzeug.utils import secure_filename
app = Flask(__name__)

@app.route("/")
def index():
    data = BaseModel('user')

    user = data.get(password="")

    if not user:
        return {"error": "User not found"}, 404
    
    
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
