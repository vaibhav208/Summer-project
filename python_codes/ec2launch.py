from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3

app = Flask(__name__)
CORS(app)  # This will handle CORS for all routes

# Function to launch an EC2 instance
def launch_ec2_instance(access_key, secret_key):
    try:
        # Create a session using the provided keys
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='ap-south-1'  # Specify your desired region
        )

        # Create EC2 resource
        ec2_resource = session.resource('ec2')

        # Launch an EC2 instance
        instance = ec2_resource.create_instances(
            ImageId='ami-02b49a24cfb95941c',  # Amazon Linux 2 AMI
            InstanceType='t2.micro',
            MinCount=1,
            MaxCount=1
        )

        return {"message": "EC2 instance launched successfully!", "instance_id": instance[0].id}

    except Exception as e:
        return {"error": str(e)}

@app.route('/ec2launch', methods=['POST'])
def ec2launch():
    data = request.form
    access_key = data.get('access_key')
    secret_key = data.get('secret_key')
    
    result = launch_ec2_instance(access_key, secret_key)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)