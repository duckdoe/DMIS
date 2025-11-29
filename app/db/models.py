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
# print(users.get(username="fortune"))


# patients = BaseModel("patients")
# patients.set(
#     first_name="Fortune",
#     last_name="Foluso",
#     dob=datetime.date(year=2015, month=10, day=26),
#     gender="male",
# )

# print(patients.get(first_name="Fortune"))