import datetime
import smtplib
from email.mime.text import MIMEText
import os
from smtplib import SMTPResponseException
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDR = os.getenv("EMAIL_ADDR")
EMAIL_PW = os.getenv("EMAIL_PW")


def send_email(email, body, subject):
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = "fortunefoluso@gmail.com"
    message["To"] = email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDR, EMAIL_PW)
            server.sendmail(message["From"], message["To"], message.as_string())
        return True
    except SMTPResponseException:
        return False


def send_login_alert(user_email):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"A new login was detected on your account at {timestamp}"
    subject = "Login Alert"

    if send_email(user_email, subject=subject, body=body):
        return True

    return False


def appointment_scheduled(email, appointment_date, appointment_time, doctor_name):
    subject = "Appointment Confirmation"
    body = f"Your appointment with Dr. {doctor_name} is scheduled for {appointment_date} at {appointment_time}."

    if send_email(email, body, subject):
        return True

    return False


def appointment_rejected(email, appointment_date, appointment_time, doctor_name):
    subject = "Appointment Rejection"
    body = f"Your appointment with Dr. {doctor_name} on {appointment_date} at {appointment_time} has been rejected."

    if send_email(email, subject, body):
        return True

    return False


def appointment_rescheduled(email, old_date, old_time, new_date, new_time, doctor_name):
    subject = "Appointment Rescheduled"
    body = f"Your appointment with Dr. {doctor_name} originally scheduled for {old_date} at {old_time} has been rescheduled to {new_date} at {new_time}."

    if send_email(email=email, body=body, subject=subject):
        return True

    return False


def message_sent(email, subjects, content, file_url):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = "Message sent"
    body = f"Details: {subjects}\n\n{content}\n\n{file_url} at {timestamp}"

    if send_email(email, subject, body):
        return True

    return False


def send_patient_email(email_to, body):
    subject = "Registration Alert"
    body = body.strip()
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = "fortunefoluso@gmail.com"
    message["To"] = email_to
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDR, EMAIL_PW)
            server.sendmail(message["From"], message["To"], message.as_string())
        return True
    except SMTPResponseException:
        return False
