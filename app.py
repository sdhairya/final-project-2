from flask import Flask, render_template, request
from pymysql import connections
import os
import random
import argparse
import boto3
import logging

app = Flask(__name__)



# Set up logging
logging.basicConfig(level=logging.INFO)

# DB connection details (from K8s secrets)
DBHOST = os.environ.get("DBHOST", "localhost")
DBUSER = os.environ.get("DBUSER", "root")
DBPWD = os.environ.get("DBPWD", "password")
DATABASE = os.environ.get("DATABASE", "employees")
DBPORT = int(os.environ.get("DBPORT", 3306))


db_conn = None
def connect_to_db():
    global db_conn
    if app.config.get("TESTING", False):
        logging.info("Skipping DB connection in test mode.")
        return
    db_conn = connections.Connection(
        host=DBHOST,
        port=DBPORT,
        user=DBUSER,
        password=DBPWD,
        db=DATABASE
    )



# Group Name and Slogan from ConfigMap
GROUP_NAME = os.environ.get("GROUP_NAME", "Awesome Devs")
SLOGAN = os.environ.get("SLOGAN", "Code. Deploy. Repeat.")

# Background image S3 details
BG_IMAGE_S3_URL = os.environ.get("BG_IMAGE_S3_URL", "")
LOCAL_BG_IMAGE_PATH = "static/download.jpeg"

# AWS credentials (from K8s secrets)
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Download the background image from S3
def download_bg_image():
    if not BG_IMAGE_S3_URL:
        logging.warning("No S3 URL provided for background image.")
        return

    try:
        s3 = boto3.client('s3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )

        bucket_name = "clo835-finalproject-bucket"
        key = "download.jpeg"
        logging.info(f"Fetching background image from: {BG_IMAGE_S3_URL, bucket_name, key}")
        s3.download_file(bucket_name, key, LOCAL_BG_IMAGE_PATH)
        logging.info("Background image downloaded successfully.")
    except Exception as e:
        logging.error(f"Failed to download background image: {e}")

# Call on startup
download_bg_image()

# # Connect to MySQL DB
# db_conn = connections.Connection(
#     host=DBHOST,
#     port=DBPORT,
#     user=DBUSER,
#     password=DBPWD,
#     db=DATABASE
# )

table = 'employee'
output = {}

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('addemp.html', bg_img=LOCAL_BG_IMAGE_PATH, group=GROUP_NAME, slogan=SLOGAN)

@app.route("/about", methods=['GET', 'POST'])
def about():
    return render_template('about.html', bg_img=LOCAL_BG_IMAGE_PATH, group=GROUP_NAME, slogan=SLOGAN)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = first_name + " " + last_name
    finally:
        cursor.close()

    return render_template('addempoutput.html', name=emp_name, bg_img=LOCAL_BG_IMAGE_PATH, group=GROUP_NAME, slogan=SLOGAN)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    return render_template("getemp.html", bg_img=LOCAL_BG_IMAGE_PATH, group=GROUP_NAME, slogan=SLOGAN)

@app.route("/fetchdata", methods=['POST'])
def FetchData():
    emp_id = request.form['emp_id']
    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location FROM employee WHERE emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (emp_id,))
        result = cursor.fetchone()
        if result:
            output["emp_id"] = result[0]
            output["first_name"] = result[1]
            output["last_name"] = result[2]
            output["primary_skills"] = result[3]
            output["location"] = result[4]
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
    finally:
        cursor.close()

    return render_template("getempoutput.html", id=output.get("emp_id", "N/A"),
                           fname=output.get("first_name", "N/A"),
                           lname=output.get("last_name", "N/A"),
                           interest=output.get("primary_skills", "N/A"),
                           location=output.get("location", "N/A"),
                           bg_img=LOCAL_BG_IMAGE_PATH, group=GROUP_NAME, slogan=SLOGAN)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', required=False)
    args = parser.parse_args()
    connect_to_db()


    app.run(host='0.0.0.0', port=81, debug=True)
