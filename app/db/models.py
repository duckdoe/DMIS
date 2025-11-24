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
