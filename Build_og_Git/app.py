from flask import Flask, request, render_template, redirect, url_for, session
import random
import smtplib
from email.message import EmailMessage
import mysql.connector
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template
from ml.predict import predict_next_day
from langchain_agent.agent import agent
load_dotenv()

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
DB_PASSWORD = os.getenv("DB_PASSWORD")
FLASK_KEY = os.getenv("FLASK_KEY")
EMAIL_ADDRESS = "shiragh.4@gmail.com"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

app = Flask(__name__)
app.secret_key = FLASK_KEY

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=DB_PASSWORD,
    database="authSystem"
)

cursor = db.cursor(dictionary=True)
otp_store = {}
reset_otp_store = {}

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        query = "SELECT * FROM users WHERE email=%s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):

            otp = random.randint(100000, 999999)
            otp_store[email] = otp

            msg = EmailMessage()
            msg.set_content(f"Your login OTP is: {otp}")
            msg['Subject'] = 'OTP Verification'
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = email

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)

            return render_template('login.html', show_otp=True, email=email)

        return render_template('login.html', error="Either Email or Password is Wrong")

    return render_template('login.html')

@app.route('/verify-otp', methods=['POST'])
def verify_otp():

    email = request.form['email']
    user_otp = request.form['otp']

    if email in otp_store and str(otp_store[email]) == user_otp:

        otp_store.pop(email)
        session['user_email'] = email

        # Get user name from database
        query = "SELECT name FROM users WHERE email=%s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        session['user_name'] = user['name'] if user else 'User'

        return redirect(url_for("dashboard"))

    return render_template(
        'login.html',
        show_otp=True,
        email=email,
        error="Wrong OTP, Try Again"
    )

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email'].lower()
        password = request.form['password']

        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters long')
        
        if not any(char.isdigit() for char in password):
            return render_template('register.html', error='Password must contain at least one number')

        check_query = "SELECT * FROM users WHERE email=%s"
        cursor.execute(check_query, (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return render_template('register.html', error='Email is already registered. Please use a different email or login.')

        hash_pass = generate_password_hash(password)
        query = "INSERT INTO users(name, email, password) VALUES (%s,%s,%s)"
        cursor.execute(query, (name, email, hash_pass))
        db.commit()

        return render_template(
            'login.html',
            success="Registration successful! You can now login."
        )

    return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    
    if request.method == 'POST':
        email = request.form['email'].lower()
        
        query = "SELECT * FROM users WHERE email=%s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        
        if not user:
            return render_template('forgot-password.html', error='Email not found. Please register first.')
        
        otp = random.randint(100000, 999999)
        reset_otp_store[email] = otp
        
        msg = EmailMessage()
        msg.set_content(f"Your password reset OTP is: {otp}\n\nIf you didn't request this, please ignore this email.")
        msg['Subject'] = 'Password Reset OTP'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
            
            return render_template('forgot-password.html', show_otp=True, email=email, success='OTP sent to your email')
        except Exception as e:
            return render_template('forgot-password.html', error='Failed to send OTP. Please try again.')
    
    return render_template('forgot-password.html')

@app.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    
    email = request.form['email']
    user_otp = request.form['otp']
    
    if email in reset_otp_store and str(reset_otp_store[email]) == user_otp:
        return render_template('forgot-password.html', show_reset=True, email=email)
    
    return render_template(
        'forgot-password.html',
        show_otp=True,
        email=email,
        error='Invalid OTP. Please try again.'
    )

@app.route('/reset-password', methods=['POST'])
def reset_password():
    
    email = request.form['email']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if len(new_password) < 6:
        return render_template('forgot-password.html', show_reset=True, email=email, error='Password must be at least 6 characters long')
    
    if not any(char.isdigit() for char in new_password):
        return render_template('forgot-password.html', show_reset=True, email=email, error='Password must contain at least one number')
    
    if new_password != confirm_password:
        return render_template('forgot-password.html', show_reset=True, email=email, error='Passwords do not match')
    
    hash_pass = generate_password_hash(new_password)
    query = "UPDATE users SET password=%s WHERE email=%s"
    cursor.execute(query, (hash_pass, email))
    db.commit()
    
    if email in reset_otp_store:
        reset_otp_store.pop(email)
    
    return render_template('login.html', success='Password reset successful! Please login with your new password.')

@app.route('/dashboard')
def dashboard():

    if 'user_email' not in session:
        return redirect(url_for("login"))

    return render_template('dashboard.html', 
                         user_email=session.get('user_email'),
                         user_name=session.get('user_name', 'User'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/pollutants/pm25')
def pm25():
    return render_template('pollutant-info/pm25.html', user_email=session.get('user_email'))

@app.route('/pollutants/pm10')
def pm10():
    return render_template('pollutant-info/pm10.html', user_email=session.get('user_email'))

@app.route('/pollutants/no2')
def no2():
    return render_template('pollutant-info/no2.html', user_email=session.get('user_email'))

@app.route('/pollutants/so2')
def so2():
    return render_template('pollutant-info/so2.html', user_email=session.get('user_email'))

@app.route('/pollutants/co')
def co():
    return render_template('pollutant-info/co.html', user_email=session.get('user_email'))

@app.route('/pollutants/o3')
def o3():
    return render_template('pollutant-info/o3.html', user_email=session.get('user_email'))

@app.route('/airchat')
def airchat():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('air-quality/airchat.html',user_email=session.get('user_email'))

@app.route('/airchat/send', methods=['POST'])
def airchat_send():

    data = request.get_json()
    user_message = data.get('message', '').lower()

    if user_message in ["hi", "hello", "hey"]:
        return {"reply": "Hello! I'm AirChat. Ask me about AQI or pollution."}

    if "what is aqi" in user_message:
        return {"reply": "AQI (Air Quality Index) measures how polluted the air is and how it affects health."}

    if "thanks" in user_message:
        return {"reply": "You're welcome! Let me know if you want to know about AQI or pollution levels."}

    if "forecast" in user_message or "today" in user_message or "aqi prediction" in user_message:
        from ml.predict import predict_next_day

        result = predict_next_day()

        return {
            "reply": f"Today's predicted AQI is {result['predicted_aqi']} ({result['category']}). "
                     f"PM2.5 prediction: {result['predicted_pm25']} µg/m³."
        }
    try:
        response = agent.run(user_message)
        return {"reply": response}

    except Exception as e:
        print("Chat error:", e)
        return {"reply": "Sorry, I'm temporarily unable to access AI insights right now."}

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/aqi")
def aqi_show():
     
    prediction = predict_next_day()
    return render_template(
        "air-quality/aqi_show.html",
        aqi=prediction["predicted_aqi"],
        aqi_low=prediction["aqi_low"],
        aqi_high=prediction["aqi_high"],
        category=prediction["category"],
        color=prediction["color"],
        transition_message=prediction.get("transition_message"),
        user_email=session.get('user_email')
    )

if __name__ == '__main__':
    app.run(debug=True, port=5001)