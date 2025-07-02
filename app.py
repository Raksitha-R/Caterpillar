from flask import Flask, render_template, request, redirect, session
import pyrebase, dropbox, os, bcrypt, json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'secret_key'

# Firebase config
# firebase_config = {
#     "apiKey": "AIzaSyBCHKvaapkyDiYSPvIS-XYatw8_4oWUEBI",
#     "authDomain": "caterpillar-fa475.firebaseapp.com",
#     "databaseURL": "https://caterpillar-fa475-default-rtdb.firebaseio.com",
#     "projectId": "caterpillar-fa475",
#     "storageBucket": "caterpillar-fa475.appspot.com",
#     "messagingSenderId": "1049817279301",
#     "appId": "1:1049817279301:web:a270bd2145757e9a88ac2c",
#     "measurementId": "G-CFJ41VV7M7"
# }
firebase_config= {
  "apiKey": "AIzaSyBDIf-8M8L_eFEarYunO5Sd1K2RSl5jcLM",
  "authDomain": "catapp-66ea7.firebaseapp.com",
  "databaseURL": "https://catapp-66ea7-default-rtdb.firebaseio.com",
  "projectId": "catapp-66ea7",
  "storageBucket": "catapp-66ea7.firebasestorage.app",
  "messagingSenderId": "11460704804",
  "appId": "1:11460704804:web:6709c59b588d467b41b6b1"
}

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Dropbox setup
dbx = dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"))

# Gemini setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/text-bison-001')


@app.route('/')
def index():
    return redirect('/login')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        users = db.child("users").get()

        for user in users.each() if users.each() else []:
            if user.val().get('email') == email:
                return render_template('signup.html', status="Email already registered.", success=False)

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db.child("users").push({
            "username": username,
            "email": email,
            "password": hashed_pw.decode('utf-8'),
            "role": "user"
        })

        return redirect('/login?status=Account created successfully&success=true')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    status = request.args.get("status")
    success = request.args.get("success") == "true"

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users = db.child("users").get()

        for user in users.each() if users.each() else []:
            data = user.val()
            if data['email'] == email:
                if bcrypt.checkpw(password.encode('utf-8'), data['password'].encode('utf-8')):
                    session['user'] = email
                    session['username'] = data.get('username', 'User')
                    session['role'] = data.get('role', 'user')
                    return redirect('/admin' if session['role'] == 'admin' else '/dashboard')
                else:
                    return render_template('login.html', status="Invalid password.", success=False)

        return render_template('login.html', status="User not found.", success=False)

    return render_template('login.html', status=status, success=success)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    summary = ''
    if request.method == 'POST':
        if 'text' in request.form and request.form['text']:
            try:
                text_input = request.form['text']
                response = model.generate_content(text_input)
                summary = response.text
            except Exception as e:
                summary = f"Gemini error: {str(e)}"
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename:
                path = f"/uploads/{file.filename}"
                dbx.files_upload(file.read(), path, mute=True)
                summary = f"Uploaded {file.filename} to Dropbox."
    return render_template('dashboard.html', summary=summary, user=session['username'])


@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        return redirect('/login')

    users = db.child("users").get()
    user_list = []
    for user in users.each() if users.each() else []:
        data = user.val()
        user_list.append({
            "key": user.key(),
            "username": data.get("username", ""),
            "email": data.get("email", ""),
            "role": data.get("role", "user")
        })

    return render_template('admin.html', users=user_list)


@app.route('/delete_user/<user_key>')
def delete_user(user_key):
    if session.get('role') == 'admin':
        db.child("users").child(user_key).remove()
    return redirect('/admin')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)