from connection import db_connection

query = """

INSERT INTO patients (name, email, password, gender, age, date_of_birth) VALUES ('Fortune', 'fortunefoluso@gmail,com, 'M', 16);

INSERT INTO patients (name, email, password, gender, age, date_of_birth) VALUES ('John doe', 'example@mail.com, 'M', 16);

INSERT INTO patients (name, email, password, gender, age, date_of_birth) VALUES ('Jane doe', 'example@mail.com, 'M', 16);

INSERT INTO department VALUES('Financial');
INSERT INTO department VALUES('Surgical');
INSERT INTO department VALUES('Dental');
INSERT INTO department VALUES('Administrative');

INSERT INTO staff(name, email, department, role) VALUES('John doe', 'example@mail.com', 'Financial', 'bursar');
INSERT INTO staff(name, email, department, role) VALUES ('Jane doe', 'example@mail.com', 'Dental', 'doctor);
INSERT INTO staff(name, email, department, role) VALUES ('John Smith', 'example@mail.com', 'Surgical', 'doctor');
INSERT INTO staff(name, email, department, role) VALUES ('Jesse Jones', 'example@mail.com', 'Administration', 'admin');
"""


if __name__ == "__main__":
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
