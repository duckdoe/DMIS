import bcrypt
"""
This file contains all the functions for querying the database.
"""

from connection import db_connection


class BaseModel:
    """
    Pyton base class with a minmal querying setup

    :params:
    table: str
    """

    def __init__(self, table):
        self.table = table

    def get(self, all=False, **kwargs):
        keys = (
            "=%s AND ".join(kwargs.keys()) + "=%s"
            if len(kwargs.keys()) > 1
            else "=%s ".join(kwargs.keys())
        )  # concatenates the keys provided in th function

        values = tuple(kwargs.values())  #  turns the values into a tuple

        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {self.table} WHERE {keys}", values)

            if all == True:
                data = cur.fetchall()
            else:
                data = cur.fetchone

    def set(self):
        pass

    def update(self):
        pass

    def delete(self):
        pass

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(),salt).decode()
    return hashed

bcrypt.hashpw("".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_hashed_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def create_user(id, username, password_hash, role):
    hash_pw = hash_password(password_hash)
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO users(username, password_hash, role)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """, (username, hash_pw, role))
        conn.commit()
def register_patients(first_name, last_name, dob, gender, email):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO patients(id, first_name, last_name, dob, gender, email)
        VALUES(%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """, (first_name, last_name, dob, gender, email))
        conn.commit()

def create_documents (patient_id, uploader_id, file_name, storage_path, mime_type, document_type):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO documents(patient_id, uploader_id, file_name, storage_path, mime_type, document_type)
        VALUES(%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """, (patient_id, uploader_id, file_name, storage_path, mime_type, document_type))
        conn.commit()

def create_visit(patient_id, doctor_id, visit_date, notes):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO visit(patient_id, doctor_id, visit_date, notes)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """, (patient_id, doctor_id, visit_date, notes))
        conn.commit()
def create_appointment(patient_id, doctor_id, preferred_date, reason):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO appointments(patient_id, doctor_id, preferred_date, reason)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """, (patient_id, doctor_id, preferred_date, reason))
        conn.commit()
def audit_logs(user_id, action, resource_type, resource_id):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO audit_logs(user_id, action, resource_type, resource_id)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """, (user_id, action, resource_type, resource_id))
        conn.commit()
