from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import openpyxl
from io import BytesIO
from datetime import datetime

app = Flask(__name__, static_folder='static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/print')
def print_page():
    return render_template('print.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    data['status'] = 'Processing'  # Default status

    try:
        if not os.path.exists('data.json'):
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump([], f)

        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                content = f.read()
                current_data = json.loads(content) if content.strip() else []
        except json.JSONDecodeError:
            # If JSON is invalid, start with an empty list
            current_data = []

        current_data.append(data)

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        return jsonify({"message": "Data saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

    # Log status change
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

app.run(host='0.0.0.0', port=81)
