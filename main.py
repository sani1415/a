
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import json
import os
import openpyxl
from io import BytesIO
from datetime import datetime
import random
import string
import hashlib

app = Flask(__name__, static_folder='static')
app.secret_key = 'madrasatul_madinah_secret_key'  # Required for session

# Generate a unique ID and password
def generate_credentials():
    # Generate a 6-digit application ID
    application_id = ''.join(random.choices(string.digits, k=6))

    # Generate a simple 8-character password
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    # Hash the password for storage
    hashed_password = hashlib.md5(password.encode()).hexdigest()

    return application_id, password, hashed_password

@app.route('/submit', methods=['POST'])
def submit():
    # Generate credentials
    application_id, password, hashed_password = generate_credentials()

    data = {
        'name': request.form.get('name'),
        'birth': request.form.get('birth'),
        'class': request.form.get('class'),
        'guardian': request.form.get('guardian'),
        'phone': request.form.get('phone'),
        'address': request.form.get('address'),
        'status': 'Processing',
        'submitted_at': datetime.now().strftime('%Y-%m-%d %I:%M %p'),
        'application_id': application_id,
        'password_hash': hashed_password,
    }

    # Save uploaded image
    image = request.files.get('photo')
    if image:
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"
        filepath = os.path.join(upload_folder, filename)
        image.save(filepath)
        data['photo'] = filename
    else:
        return jsonify({"error": "Photo is required"}), 400

    try:
        if not os.path.exists('data.json'):
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump([], f)

        with open('data.json', 'r', encoding='utf-8') as f:
            content = f.read()
            current_data = json.loads(content) if content.strip() else []

        current_data.append(data)

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        # Create empty message history for this applicant
        if not os.path.exists('messages.json'):
            with open('messages.json', 'w', encoding='utf-8') as f:
                json.dump({}, f)

        with open('messages.json', 'r', encoding='utf-8') as f:
            content = f.read()
            messages = json.loads(content) if content.strip() else {}

        messages[application_id] = []

        with open('messages.json', 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

        # Return success with credentials
        return jsonify({
            "message": "Data saved successfully", 
            "application_id": application_id, 
            "password": password
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/data')
def data():
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/update-status/<int:index>', methods=['POST'])
def update_status(index):
    new_status = request.json.get('status')
    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    with open('data.json', 'r', encoding='utf-8') as f:
        students = json.load(f)

    if index < 0 or index >= len(students):
        return jsonify({'error': 'Invalid index'}), 400

    students[index]['status'] = new_status

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(students, f, ensure_ascii=False, indent=2)

    log_entry = {
        'index': index,
        'status': new_status,
        'timestamp': timestamp
    }

    if not os.path.exists('status_log.json'):
        with open('status_log.json', 'w', encoding='utf-8') as f:
            json.dump([], f)

    with open('status_log.json', 'r', encoding='utf-8') as f:
        logs = json.load(f)

    logs.append(log_entry)

    with open('status_log.json', 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    return jsonify({'message': 'Status updated successfully'})

@app.route('/export-excel')
def export_excel():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            students = json.load(f)
    except FileNotFoundError:
        students = []

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    headers = ['Name', 'Birth Date', 'Class', 'Guardian', 'Phone', 'Address', 'Status']
    ws.append(headers)

    for student in students:
        ws.append([
            student.get('name', ''),
            student.get('birth', ''),
            student.get('class', ''),
            student.get('guardian', ''),
            student.get('phone', ''),
            student.get('address', ''),
            student.get('status', 'Processing')
        ])

    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name='students.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/status-log')
def status_log():
    try:
        if not os.path.exists('status_log.json'):
            with open('status_log.json', 'w', encoding='utf-8') as f:
                json.dump([], f)
            return jsonify([])

        with open('status_log.json', 'r', encoding='utf-8') as f:
            content = f.read()
            logs = json.loads(content) if content.strip() else []
        return jsonify(logs)
    except Exception as e:
        print(f"Error in status_log route: {str(e)}")
        return jsonify([])

@app.route('/applicant-login', methods=['GET'])
def applicant_login_page():
    return render_template('applicant_login.html')

@app.route('/applicant-login', methods=['POST'])
def applicant_login():
    application_id = request.form.get('application_id')
    password = request.form.get('password')

    # Hash the password to compare
    password_hash = hashlib.md5(password.encode()).hexdigest()

    with open('data.json', 'r', encoding='utf-8') as f:
        students = json.load(f)

    for student in students:
        if student.get('application_id') == application_id and student.get('password_hash') == password_hash:
            # Store in session
            session['application_id'] = application_id
            session['student_name'] = student.get('name')
            return redirect(url_for('messaging'))

    # If we get here, login failed
    return render_template('applicant_login.html', error="Invalid credentials. Please try again.")

@app.route('/messaging')
def messaging():
    if 'application_id' not in session:
        return redirect(url_for('applicant_login_page'))

    application_id = session['application_id']

    # Get student data
    with open('data.json', 'r', encoding='utf-8') as f:
        students = json.load(f)

    student = None
    for s in students:
        if s.get('application_id') == application_id:
            student = s
            break

    if not student:
        session.clear()
        return redirect(url_for('applicant_login_page'))

    # Get message history
    with open('messages.json', 'r', encoding='utf-8') as f:
        all_messages = json.load(f)

    messages = all_messages.get(application_id, [])

    return render_template('messaging.html', student=student, messages=messages)

@app.route('/send-message', methods=['POST'])
def send_message():
    if 'application_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    application_id = session['application_id']
    message_text = request.json.get('message', '')

    if not message_text.strip():
        return jsonify({"error": "Message cannot be empty"}), 400

    # Create message object
    message = {
        'text': message_text,
        'sent_by': 'applicant',
        'timestamp': datetime.now().strftime('%Y-%m-%d %I:%M %p')
    }

    # Add to messages.json
    with open('messages.json', 'r', encoding='utf-8') as f:
        all_messages = json.load(f)

    if application_id not in all_messages:
        all_messages[application_id] = []

    all_messages[application_id].append(message)

    with open('messages.json', 'w', encoding='utf-8') as f:
        json.dump(all_messages, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True, "message": message})

@app.route('/admin-send-message', methods=['POST'])
def admin_send_message():
    application_id = request.json.get('application_id')
    message_text = request.json.get('message', '')

    if not application_id or not message_text.strip():
        return jsonify({"error": "Application ID and message are required"}), 400

    # Create message object
    message = {
        'text': message_text,
        'sent_by': 'admin',
        'timestamp': datetime.now().strftime('%Y-%m-%d %I:%M %p')
    }

    # Add to messages.json
    with open('messages.json', 'r', encoding='utf-8') as f:
        all_messages = json.load(f)

    if application_id not in all_messages:
        all_messages[application_id] = []

    all_messages[application_id].append(message)

    with open('messages.json', 'w', encoding='utf-8') as f:
        json.dump(all_messages, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True, "message": message})

@app.route('/get-messages/<application_id>')
def get_messages(application_id):
    # For admin to get messages for a specific applicant
    with open('messages.json', 'r', encoding='utf-8') as f:
        all_messages = json.load(f)

    messages = all_messages.get(application_id, [])
    return jsonify(messages)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin-messaging')
def admin_messaging():
    return render_template('admin_messaging.html')

@app.route('/print')
def print_student():
    index = request.args.get('index', type=int)
    
    with open('data.json', 'r', encoding='utf-8') as f:
        students = json.load(f)
    
    if index is None or index < 0 or index >= len(students):
        return "Invalid student index"
    
    student = students[index]
    return render_template('print.html', student=student)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
