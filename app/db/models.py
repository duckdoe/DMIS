"""
This file contains all the functions for querying the database.
"""

from connection import db_connection
from Utils.hash import hash_password,verify
connection = db_connection()

def create_user(name, username, email, password, role='user'):
    with connection.cursor() as cursor:
        hash_pw = hash_password(password)
        cursor.execute("""
            INSERT INTO desk_user (name, username, email, password, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, username, email, hash_pw, role))
    connection.commit()

def get_user_by_username(username):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, username, email, password, role
            FROM desk_user
            WHERE username = %s
        """, (username,))
        return cursor.fetchone()

def delete_user(user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM desk_user WHERE id = %s
        """, (user_id,))
    connection.commit()

def create_patient(first_name, last_name, dob, gender, phone, email):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO patients (first_name, last_name, dob, gender, phone, email)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, dob, gender, phone, email))
    connection.commit()
    
def get_patient(patient_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM patients WHERE id = %s
        """, (patient_id,))
        return cursor.fetchone()

def search_patients(keyword):
    like = f"%{keyword}%"
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM patients
            WHERE first_name LIKE %s OR last_name LIKE %s OR phone LIKE %s
        """, (like, like, like))
        return cursor.fetchall()

def upload_document(patient_id, uploader_id, file_name, storage_path, mime_type, doc_type):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO documents (patient_id, uploader_id, file_name, storage_path, mime_type, document_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (patient_id, uploader_id, file_name, storage_path, mime_type, doc_type))
    connection.commit()

def get_patient_documents(patient_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM documents
            WHERE patient_id = %s
        """, (patient_id,))
        return cursor.fetchall()
    
def create_appointment(patient_id, doctor_id, preferred_date, reason):
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO appointments (patient_id, doctor_id, preferred_date, reason)
            VALUES (%s, %s, %s, %s)
        """, (patient_id, doctor_id, preferred_date, reason))
    connection.commit()

def get_pending_appointments(doctor_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM appointments
            WHERE doctor_id = %s AND status = 'PENDING'
        """, (doctor_id,))
        return cursor.fetchall()




