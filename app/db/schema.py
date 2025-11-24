from connection import db_connection

query = """

CREATE TABLE IF NOT EXISTS patients (
    patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password TEXT NOT NULL,
    gender VARCHAR(1) CHECK NOT NULL,
    age SMALLINT NOT NULL,
    date_of_birth DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS department (
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS staff (
    staff_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCAHR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    department VARCHAR(255) REFERENCES departments(name) NOT NULL,
    role VARCHAR(20) DEFAULT 'staff'
);

CREATE TABLE IF NOT EXISTS appointments (
    doctor_id UUID REFERENCES staff(staff_id),
    patient_id UUID REFERENCES patients(patient_id) NOT NULL,
    description TEXT,
    date TIMESTAMP,
    status VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS billings(
    billing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id) NOT NULL,
    amount_owed VARCAHR(255) NOT NULL,
    cleared BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_id UUID REFERENCES billings(billing_id),
    amount_paind VARCHAR(255) NOT NULL,
    payment_date TIMESTAMP DEFAULT now(),
    status VARCHAR(10) DEFAULT pending
);

CREATE TABLE IF NOT EXISTS patient_records (
    patient_id UUID REFERENCES patients(patient_id),
    blood_type VARCAHR(3),
    height SMALLINT,
    weight SMALLINT,
    address TEXT
);

CREATE TABLE IF NOT EXISTS doctor_patient (
    doctor_id UUID REFERENCES staff(staff_id),
    patient_id UUID REFERENCES patients(patient_id)
);

"""

if __name__ == "__main__":
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query)

        conn.commit()
