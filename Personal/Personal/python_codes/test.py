import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import cv2
import numpy as np
import base64
import pyttsx3
from gtts import gTTS
import boto3
from twilio.rest import Client
import requests
from googlesearch import search
import pandas as pd
from PIL import Image

app = Flask(__name__)
CORS(app)  # Enable CORS

# face detect and image crop

def capture_and_process_image():
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    ret, frame = cap.read()

    if not ret:
        return None, "Failed to capture image"

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        return None, "No face detected"

    for (x, y, w, h) in faces:
        face = frame[y:y+h, x:x+w]
        face_resized = cv2.resize(face, (w//2, h//2))
        frame[0:face_resized.shape[0], 0:face_resized.shape[1]] = face_resized
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

    _, img_encoded = cv2.imencode('.jpg', frame)
    return img_encoded, None

@app.route('/capture', methods=['POST'])
def capture():
    img_encoded, error = capture_and_process_image()
    
    if error:
        return jsonify({'error': error}), 400
    
    img = Image.open(io.BytesIO(img_encoded.tobytes()))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return send_file(io.BytesIO(img_byte_arr), mimetype='image/jpeg')

# Data processing functions
def load_data(file):
    """Load data from a CSV file."""
    try:
        return pd.read_csv(file)
    except Exception as e:
        raise ValueError(f"Error loading CSV file: {e}")

def clean_data(df):
    """Clean the dataset by handling missing values and duplicates."""
    try:
        df = df.dropna()
        df = df.drop_duplicates()
        return df
    except Exception as e:
        raise ValueError(f"Error cleaning data: {e}")

def summarize_data(df):
    """Generate a summary of the dataset."""
    try:
        summary = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'info': str(df.info()),  # Convert DataFrame info to string
            'description': df.describe(include='all').to_dict()  # Convert DataFrame description to dict
        }
        return summary
    except Exception as e:
        raise ValueError(f"Error summarizing data: {e}")

@app.route('/process_data', methods=['POST'])
def process_data():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        df = load_data(file)
        df_cleaned = clean_data(df)
        summary = summarize_data(df_cleaned)
        return jsonify(summary)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500



#top 5 searches

def google_search(query, num_results=5):
    top_results = []
    try:
        for idx, result in enumerate(search(query), start=1):
            top_results.append(result)
            if idx >= num_results:
                break
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return top_results

@app.route('/search', methods=['GET'])
def search_query():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    results = google_search(query)
    return jsonify({"results": results})


# to get live location

def get_current_location():
    try:
        response = requests.get('https://ipinfo.io/json')
        data = response.json()
        location = {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "location": data.get("loc")
        }
        return location
    except Exception as e:
        return {"error": str(e)}

@app.route('/get-location', methods=['GET'])
def get_location_route():
    try:
        location = get_current_location()
        return jsonify(location)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# to send single mail
sender_email = "yadupalchaudhary63@gmail.com"  # Replace with your email
sender_password = "cdsp eujr dins ztgn"  # Replace with your app-specific password

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.json
        receiver_email = data.get('receiver_email')
        subject = data.get('subject')
        body = data.get('body')

        if not receiver_email or not subject or not body:
            return jsonify({'error': 'Receiver email, subject, and body are required'}), 400

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        return jsonify({'message': 'Email sent successfully!'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# TO send sms using twilio

account_sid = 'AC14a99c63d601d41f512c3bdbe7c9e5eb'
auth_token = 'e2799e43a4fae6b93e2a1a0bc6d2349b'

# Initialize Twilio client
client = Client(account_sid, auth_token)

@app.route('/send_sms', methods=['POST'])
def send_sms():
    try:
        data = request.json
        to = data.get('to')
        body = data.get('body')

        if not to or not body:
            return jsonify({'error': 'Recipient number and message body are required'}), 400

        message = client.messages.create(
            body=body,
            from_='+15673444970',  # Replace with your Twilio phone number
            to=to
        )

        return jsonify({'message': 'SMS sent successfully!', 'Message SID': message.sid})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Function to send bulk emails
def send_bulk_emails(sender_email, sender_password, subject, body, recipients):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  
        server.login(sender_email, sender_password)

        for recipient in recipients:
            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = recipient
            message['Subject'] = subject
            
            message.attach(MIMEText(body, 'plain'))
            
            server.sendmail(sender_email, recipient, message.as_string())
            print(f"Email sent to {recipient}")
        
        print("All emails sent successfully!")
        return "Emails sent successfully!"
    
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"
    
    finally:
        server.quit()

@app.route('/send_emails', methods=['POST'])
def send_emails():
    data = request.json
    subject = data.get('subject')
    body = data.get('body')
    recipients = data.get('recipients')
    
    sender_email = "yadupalchaudhary63@gmail.com"  # Replace with your email
    sender_password = "cdsp eujr dins ztgn"  # Replace with your app-specific password
    
    response = send_bulk_emails(sender_email, sender_password, subject, body, recipients)
    return jsonify({'message': response})

# Python - String to Audio Conversion
@app.route('/stringtoaudio', methods=['POST'])
def string_to_audio():
    data = request.json
    text = data.get('text', '')
    if text:
        audio_buffer = io.BytesIO()
        tts = gTTS(text, lang='en')
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return send_file(
            audio_buffer,
            as_attachment=True,
            mimetype='audio/mpeg',
            download_name='output.mp3'
        )
    else:
        return jsonify({'error': 'No text provided'}), 400
    
# AWS - Launch EC2 Instance
@app.route('/launch-ec2', methods=['POST'])
def launch_ec2():
    try:
        data = request.json
        aws_access_key = data['aws_access_key']
        aws_secret_key = data['aws_secret_key']
        region = data['region']
        instance_name = data['instance_name']

        ec2 = boto3.client(
            'ec2',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )

        response = ec2.run_instances(
            ImageId='ami-0c55b159cbfafe1f0',
            InstanceType='t2.micro',
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': instance_name}]
            }]
        )

        instance_id = response['Instances'][0]['InstanceId']
        return jsonify({"message": "EC2 Instance launched successfully!", "Instance ID": instance_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)