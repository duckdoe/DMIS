import datetime

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from dotenv import load_dotenv
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def send_email(receiver_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False



def send_login_alert(user_email):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"A new login was detected on your account at {timestamp}"
    subject = "Login Alert"

    if send_email(user_email,subject=subject,body=body):
        return True

    return False

def appointment_scheduled(email,appointment_date,appointment_time,doctor_name):
    subject = "Appointment Confirmation"
    body = f"Your appointment with Dr. {doctor_name} is scheduled for {appointment_date} at {appointment_time}."

    if send_email(email,subject,body):
        return True

    return False

def appointment_rejected(email,appointment_date,appointment_time,doctor_name):
    subject = "Appointment Rejection"
    body = f"Your appointment with Dr. {doctor_name} on {appointment_date} at {appointment_time} has been rejected."

    if send_email(email,subject,body):
        return True

    return False

def appointment_rescheduled(email,old_date,old_time,new_date,new_time,doctor_name):
    subject = "Appointment Rescheduled"
    body = f"Your appointment with Dr. {doctor_name} originally scheduled for {old_date} at {old_time} has been rescheduled to {new_date} at {new_time}."

    if send_email(email,subject,body):
        return True

    return False

def message_sent(email,subjects,content,file_url):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject= "Message sent"
    body = f"Details: {subjects}\n\n{content}\n\n{file_url} at {timestamp}"

    if send_email(email,subject,body):
        return True

    return False


