
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import json
import os
import openpyxl
from io import BytesIO
from datetime import datetime
import random
import string
import hashlib
import uuid

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

# Load deleted applicants data
def load_deleted_applicants():
    try:
        if not os.path.exists('deleted_applicants.json'):
            with open('deleted_applicants.json', 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []

        with open('deleted_applicants.json', 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content.strip() else []
    except Exception as e:
        print(f"Error loading deleted applicants: {str(e)}")
        return []

# Save deleted applicants data
def save_deleted_applicants(data):
    with open('deleted_applicants.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

@app.route('/delete-applicant/<int:index>', methods=['POST'])
def delete_applicant(index):
    try:
        reason = request.json.get('reason', '')
        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')

        # Load current applicants
        with open('data.json', 'r', encoding='utf-8') as f:
            students = json.load(f)

        if index < 0 or index >= len(students):
            return jsonify({'error': 'Invalid index'}), 400

        # Get the applicant to delete
        applicant = students[index]

        # Get application_id for message handling
        application_id = applicant.get('application_id')

        # Add deletion metadata
        applicant['id'] = str(uuid.uuid4())  # Generate unique ID for retrieval
        applicant['deleted_at'] = timestamp
        applicant['delete_reason'] = reason

        # Add to deleted applicants
        deleted_applicants = load_deleted_applicants()
        deleted_applicants.append(applicant)
        save_deleted_applicants(deleted_applicants)

        # Archive messages if they exist
        if application_id:
            with open('messages.json', 'r', encoding='utf-8') as f:
                messages = json.load(f)

            if application_id in messages:
                # Either archive messages or just keep them in place
                # Option 1: Keep them in the same file but mark as deleted
                messages[application_id + '_deleted'] = messages[application_id]
                del messages[application_id]

                with open('messages.json', 'w', encoding='utf-8') as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)

        # Remove from active applicants
        students.pop(index)
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(students, f, ensure_ascii=False, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/deleted-data')
def deleted_data():
    deleted_applicants = load_deleted_applicants()
    return jsonify(deleted_applicants)

@app.route('/deleted-applicants')
def deleted_applicants():
    return render_template('deleted_applicants.html')

@app.route('/restore-applicant/<applicant_id>', methods=['POST'])
def restore_applicant(applicant_id):
    try:
        # Load deleted applicants
        deleted_applicants = load_deleted_applicants()

        # Find the applicant to restore
        applicant_index = -1
        applicant = None
        for i, a in enumerate(deleted_applicants):
            if a.get('id') == applicant_id:
                applicant_index = i
                applicant = a
                break

        if applicant_index < 0 or not applicant:
            return jsonify({'error': 'Applicant not found'}), 404

        # Remove deletion metadata
        if 'id' in applicant:
            del applicant['id']
        if 'deleted_at' in applicant:
            del applicant['deleted_at']
        if 'delete_reason' in applicant:
            del applicant['delete_reason']

        # Add to active applicants
        with open('data.json', 'r', encoding='utf-8') as f:
            students = json.load(f)

        students.append(applicant)

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(students, f, ensure_ascii=False, indent=2)

        # Restore messages if they exist
        application_id = applicant.get('application_id')
        if application_id:
            with open('messages.json', 'r', encoding='utf-8') as f:
                messages = json.load(f)

            if application_id + '_deleted' in messages:
                messages[application_id] = messages[application_id + '_deleted']
                del messages[application_id + '_deleted']

                with open('messages.json', 'w', encoding='utf-8') as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)

        # Remove from deleted applicants
        deleted_applicants.pop(applicant_index)
        save_deleted_applicants(deleted_applicants)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/mark-messages-read/<application_id>', methods=['POST'])
def mark_messages_read(application_id):
    with open('messages.json', 'r', encoding='utf-8') as f:
        all_messages = json.load(f)

    # If this applicant has messages
    if application_id in all_messages:
        # Mark all messages as read by adding a 'read' flag
        for message in all_messages[application_id]:
            if message.get('sent_by') == 'applicant':
                message['read'] = True

        # Save updated messages
        with open('messages.json', 'w', encoding='utf-8') as f:
            json.dump(all_messages, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True})

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
