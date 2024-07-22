from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# Paths to databases
events_db_path = r"C:\Users\Tanisi\OneDrive\Desktop\Flask\venv\IndicoNoticePrint-main\events (4).db"
registrations_db_path = r"C:\Users\Tanisi\OneDrive\Desktop\Flask\venv\IndicoNoticePrint-main\registrations.db"

# Function to clean HTML tags from a string
def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text()

# Function to format dates and extract timezones
def format_date_and_timezone(date_str):
    try:
        date_part, timezone_part = date_str.split(' ', 1)
        date_obj = datetime.strptime(date_part, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d")
        day = date_obj.day
        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        formatted_date = formatted_date + suffix + date_obj.strftime(", %Y")
        timezone = timezone_part.split(' ')[0]
        return formatted_date, timezone
    except ValueError:
        return "Invalid date", "Unknown timezone"

# Function to fetch events from Indico API
def fetch_events(category_number, start_date, end_date):
    url = f"https://indico.cern.ch/export/categ/{category_number}.json?from={start_date}&to={end_date}&pretty=yes"
    response = requests.get(url)

    events_data = []

    if response.status_code == 200:
        json_data = response.json()
        for event in json_data.get("results", []):
            title = event.get("title", "N/A")
            start_date = event.get("startDate", "N/A")
            end_date = event.get("endDate", "N/A")
            start_time = event.get("timezone", "N/A")
            location = event.get("location", "N/A")
            description = event.get("description", "N/A")
            url = event.get("url", "N/A")

            clean_description = clean_html(description)

            formatted_start_date, start_timezone = format_date_and_timezone(start_date)
            formatted_end_date, end_timezone = format_date_and_timezone(end_date)

            events_data.append({
                "Title": title,
                "Start Date": formatted_start_date,
                "Start Time": start_time,
                "Start Timezone": start_timezone,
                "End Date": formatted_end_date,
                "End Timezone": end_timezone,
                "Category Number": category_number,
                "Location": location,
                "Description": clean_description,
                "URL": url
            })
    else:
        print(f"Failed to fetch data for category {category_number}, status code: {response.status_code}")

    return events_data

# Function to retrieve conference event details from the database
def get_conference_events(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category_id, title, meeting_type, start_date, end_date, description, speaker, affiliation, url FROM events")
    events = [{
        "ID": row[0],
        "Category ID": row[1] or "No info",
        "Title": row[2] or "No info",
        "Meeting Type": row[3] or "No info",
        "Start Date": format_date_and_timezone(row[4])[0] if row[4] else "No info",
        "Start Timezone": format_date_and_timezone(row[4])[1] if row[4] else "No info",
        "End Date": format_date_and_timezone(row[5])[0] if row[5] else "No info",
        "End Timezone": format_date_and_timezone(row[5])[1] if row[5] else "No info",
        "Description": row[6] or "No info",
        "Speaker": row[7] or "No info",
        "Affiliation": row[8] or "No info",
        "URL": row[9] or "No info"
    } for row in cursor.fetchall()]
    conn.close()
    return events

# Function to insert registration information into the database
def insert_registration(name, email, phone):
    conn = sqlite3.connect(registrations_db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO registrations (name, email, phone)
        VALUES (?, ?, ?)
    ''', (name, email, phone))
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    conference_events = get_conference_events(events_db_path)
    return render_template("impo.html", conference_events=conference_events, forPrint=False)

@app.route("/process_form", methods=["POST"])
def process_form():
    try:
        view = request.form['view']
        category_number = request.form['category_number']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
    except KeyError as e:
        return f"Missing form field: {e.args[0]}", 400

    events_data = get_conference_events(events_db_path)
    return render_template(view, events_data=events_data, forPrint=True)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            phone = request.form.get('phone', '')
            insert_registration(name, email, phone)
            return redirect(url_for('register_success'))
        except KeyError as e:
            return f"Missing form field: {e.args[0]}", 400

    return render_template('register.html')

@app.route("/register_success")
def register_success():
    return 'Registration successful!'

if __name__ == "__main__":
    app.run(debug=True, port=3000)
