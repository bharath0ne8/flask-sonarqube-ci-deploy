from flask import Flask, jsonify, request
from flask_restful import Resource, Api
import requests
import smtplib
import ssl
from random import randint
from cachetools import cached, TTLCache
from constants import *  # Ensure this contains your configuration variables
from datetime import datetime
from models import *
from firebase_admin import credentials, auth
import firebase_admin
import random

app = Flask(__name__)
api = Api(app)

@cached(cache=TTLCache(maxsize=1024, ttl=600))
def cache_code(email_id):
    return randint(10000, 99999)  # Generate a 5-digit code

class EmailOtpGeneration(Resource):
    def post(self):
        try:
            data = request.get_json()
            response = self.verify_email(data)
            return jsonify(response)
        except Exception as e:
            return jsonify({"error": str(e)})

    def verify_email(self, data):
        email_id = data.get('emailid')
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Amanat_App_Dev.temp_user WHERE email = %s;", (email_id,))
            user = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as db_error:
            return {"status": "error", "message": str(db_error)}

        if user is None:
            code = cache_code(email_id)
            if self.send_email(email_id, code):
                if self.save_otp(email_id,code):
                    return {"status": "success", "message": "Verification email sent"}
            else:
                return {"status": "error", "message": "Failed to send email"}
        else:
            return {"status": "error", "message": "Email already exists"}

    def send_email(self, recipient_email, code):
        host = 'smtp.gmail.com'
        port = 587
        sender_email = otp_email
        sender_password = otp_password
        subject = "Amanat App Email Verification"
        body = f"Hi,\n\nYOUR EMAIL VERIFICATION CODE IS {code}.\n\nTeam\n\nTHIS IS A SYSTEM GENERATED EMAIL - PLEASE DO NOT REPLY DIRECTLY TO THIS EMAIL."

        message = f"From: {sender_email}\nTo: {recipient_email}\nSubject: {subject}\n\n{body}"
        
        try:
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, message)
            return True
        except Exception as ex:
            print(ex)
            return False
    
    def save_otp(self, email_id, code):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Use current timestamp for created_date and expire_date
            created_date = datetime.now()
            expire_date = created_date + timedelta(minutes=3)  # OTP valid for 3 minutes
            cur.execute("INSERT INTO Amanat_App_Dev.email_otp (email, otp, created_date, expire_date) VALUES (%s, %s, %s, %s);",(email_id, code, created_date, expire_date))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as db_error:
            print(f"Database error: {db_error}")
            return False

class EmailOtpVerification(Resource):
    def post(self):
        try:
            data = request.get_json()
            response = self.verify_email_code(data)
            return jsonify(response)
        except Exception as e:
            return jsonify({"error": str(e)})

    def verify_email_code(self, data):
        email_id = data.get('emailid')
        code = data.get('code')

        try:
            conn = get_db_connection()  # Implement this function to get your database connection
            cur = conn.cursor()

            # Fetch the OTP and expiration date
            cur.execute(
                "SELECT otp, expire_date FROM Amanat_App_Dev.email_otp WHERE email = %s ORDER BY created_date DESC LIMIT 1;",
                (email_id,)
            )
            record = cur.fetchone()

            if record is None:
                cur.close()
                conn.close()
                return {"status": "error", "message": "No OTP found for this email"}

            otp, expire_date = record

            if datetime.now() > expire_date:
                cur.close()
                conn.close()
                return {"status": "error", "message": "OTP expired"}

            if otp == code:
                # Save email and created_date in temp_user table
                created_date = datetime.now()
                cur.execute(
                    "INSERT INTO Amanat_App_Dev.temp_user (email, created_date) VALUES (%s, %s);",
                    (email_id, created_date)
                )
                conn.commit()
                
                cur.close()
                conn.close()
                return {"status": "success", "message": "Email code valid, user created"}
            else:
                cur.close()
                conn.close()
                return {"status": "error", "message": "Invalid email code"}

        except Exception as db_error:
            return {"status": "error", "message": str(db_error)}
    
# Initialize Firebase Admin SDK
cred = credentials.Certificate(r'C:\Users\aksha\Desktop\Amanat\amanat-f3dc2-firebase-adminsdk-qvmo1-8b7c075322.json')
firebase_admin.initialize_app(cred)

# In-memory storage for OTPs (consider using a database for production)
otp_storage = {}

class MobileOtpGeneration(Resource):
    def post(self):
        try:
            data = request.get_json()
            mobile_number = data.get('mobileNumber')
            otp = random.randint(10000, 99999)  # Generate a 5-digit OTP

            # Send OTP using Firebase
            verification_id = auth.create_verification_id(mobile_number)

            # Store OTP with expiration time
            otp_storage[mobile_number] = {
                'otp': otp,
                'verification_id': verification_id,
                'expire_at': datetime.now() + timedelta(minutes=3)
            }

            # Simulate sending OTP
            print(f"Sending OTP: {otp} to {mobile_number} via SMS.")

            return {"status": "success", "message": "OTP sent via SMS"}
        except Exception as e:
            print(e)
            return jsonify({"error": str(e)})

class MobileOtpVerification(Resource):
    def post(self):
        try:
            data = request.get_json()
            mobile_number = data.get('mobileNumber')
            otp = data.get('otp')

            # Check if the OTP exists and has not expired
            if mobile_number in otp_storage:
                stored_otp_data = otp_storage[mobile_number]
                if datetime.now() > stored_otp_data['expire_at']:
                    return {"status": "error", "message": "OTP expired"}
                
                if stored_otp_data['otp'] == otp:
                    # OTP is valid, perform actions like creating a user or logging in
                    del otp_storage[mobile_number]  # Clear the OTP after use
                    return {"status": "success", "message": "OTP verified, user created"}
                else:
                    return {"status": "error", "message": "Invalid OTP"}
            else:
                return {"status": "error", "message": "No OTP found for this mobile number"}

        except Exception as e:
            return jsonify({"error": str(e)})


# API Routes
api.add_resource(EmailOtpGeneration, "/api/emailotp")
api.add_resource(EmailOtpVerification, "/api/verifyemailotp")
api.add_resource(MobileOtpGeneration, "/api/mobileotp")
api.add_resource(MobileOtpVerification, "/api/verifymobileotp")

if __name__ == "__main__":
    app.run(debug=True)
