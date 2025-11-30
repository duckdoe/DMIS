"""
This file contains all the functions for querying the database.
"""
from .connection import db_connection


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
        )  # concatenates the keys provided in th function

        values = tuple(kwargs.values())  #  turns the values into a tuple

        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {self.table} WHERE {keys}", values)

            if all == True:
                data = cur.fetchall()
            else:
                data = cur.fetchone()

        return data

    def set(self, **kwargs):
        key_params = ""
        keys = ", ".join(kwargs.keys())

        if len(kwargs.keys()) > 0:
            for i in range(len(kwargs.keys())):
                if len(kwargs.keys()) - 1 == i:
                    key_params += "%s"
                    continue

                key_params += "%s, "

        values = tuple(kwargs.values())

        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""INSERT INTO {self.table}({keys}) VALUES({key_params})""", (values)
            )
            conn.commit()

    def update(self, where, **kwargs):
        keys = "=%s, ".join(kwargs.keys()) + "=%s"
        clause_keys = "=%s AND ".join(where.keys()) + "=%s "
        clause_values = tuple(where.values())

        values = tuple(kwargs.values()) + clause_values

        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""UPDATE {self.table} SET {keys} WHERE {clause_keys}""", (values)
            )
            conn.commit()

    def delete(self, **kwargs):
        keys = "=%s, ".join(kwargs.keys()) + "=%s"
        values = tuple(kwargs.values())

        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""DELETE FROM {self.table} WHERE {keys}""", values)
            conn.commit()

    def search_patients_like(self, query):
       like = f"%{query}%"
       with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM patients
            WHERE name LIKE %s
            OR phone LIKE %s
            OR email LIKE %s
        """, (like, like, like))
        return cur.fetchall()


# users = BaseModel("users")

# users.set(username="fortune", password_hash="fortune123", role="doctor")
# users.update(
#     password_hash="duckdb123",
#     where={
#         "username": "fortune",
#     },
# )

# users.delete(username="fortune")
# user = users.get(username="fortune")


# patients = BaseModel("patients")
# patients.set(
#     first_name="Fortune",
#     last_name="Foluso",
#     dob=datetime.date(year=2015, month=10, day=26),
#     gender="male",
# )

# print(patients.get(first_name="Fortune"))


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt).decode()
    return hashed


bcrypt.hashpw("".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_hashed_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_user(username, password_hash, role):
    hash_pw = hash_password(password_hash)
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO users(username, password_hash, role)
        VALUES(%s, %s, %s)
        RETURNING id;
        """,
            (username, hash_pw, role),
        )
        conn.commit()


def register_patients(first_name, last_name, dob, gender, email):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO patients(first_name, last_name, dob, gender, email)
        VALUES(%s, %s, %s, %s, %s)
        RETURNING id;
        """,
            (first_name, last_name, dob, gender, email),
        )
        conn.commit()


def create_documents(
    patient_id, uploader_id, file_name, storage_path, mime_type, document_type
):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO documents(patient_id, uploader_id, file_name, storage_path, mime_type, document_type)
        VALUES(%s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
            (
                patient_id,
                uploader_id,
                file_name,
                storage_path,
                mime_type,
                document_type,
            ),
        )
        conn.commit()


def create_visit(patient_id, doctor_id, visit_date, notes):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO visit(patient_id, doctor_id, visit_date, notes)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """,
            (patient_id, doctor_id, visit_date, notes),
        )
        conn.commit()


def create_appointment(patient_id, doctor_id, preferred_date, reason):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO appointments(patient_id, doctor_id, preferred_date, reason)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """,
            (patient_id, doctor_id, preferred_date, reason),
        )
        conn.commit()


def audit_logs(user_id, action, resource_type, resource_id):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO audit_logs(user_id, action, resource_type, resource_id)
        VALUES(%s, %s, %s, %s)
        RETURNING id;
        """,
            (user_id, action, resource_type, resource_id),
        )
        conn.commit()
