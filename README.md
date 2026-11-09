# Smart Queue Management System — Hospital Registration

A beginner-friendly Flask + SQLite web application for a college project.

## Features

- Patient registration with department selection
- Unique daily queue tokens (A001, A002, ...)
- Patient token page and estimated wait (demo assumption: 5 minutes per person ahead)
- Staff dashboard: call next, complete service, cancel a waiting token
- Public queue display that refreshes every five seconds
- SQLite SQL database created automatically on first run

## Folder structure

```text
smart_queue_management_system/
├── app.py
├── requirements.txt
├── README.md
├── queue.db                 # created automatically after first run
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── token.html
│   ├── staff.html
│   └── display.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## Requirements

- Python 3.10 or newer
- Internet is not required after Flask is installed
- VS Code is optional

## Setup on Windows

1. Extract the ZIP file.
2. Open the extracted `smart_queue_management_system` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run:

   ```bat
   .venv\Scripts\activate.bat
   ```

6. Install Flask:

   ```powershell
   python -m pip install -r requirements.txt
   ```

7. Start the application:

   ```powershell
   python app.py
   ```

8. Open `http://127.0.0.1:5000` in your browser.

## Pages

- Patient registration: `http://127.0.0.1:5000/`
- Staff dashboard: `http://127.0.0.1:5000/staff`
- Public display: `http://127.0.0.1:5000/display`
- Health check: `http://127.0.0.1:5000/health`

Stop the server with Ctrl+C in the terminal.

## How to demonstrate

1. Open the registration page and register a demo patient in General Medicine.
2. Note the generated token.
3. Register a second demo patient in Pediatrics.
4. Open the staff dashboard in another browser tab.
5. Click **Call next patient**. The first patient becomes `Serving`.
6. Open the public display. The current token and waiting list should update within five seconds.
7. On the staff dashboard, click **Complete** for the serving patient.
8. Click **Call next patient** to serve the second patient.
9. Confirm that the completed patient is no longer in the active queue.

## Database

SQLite stores data in `queue.db`, which is created beside `app.py`. The `patients` table includes:

- `id`: primary key
- `token_number`: integer sequence for the day
- `token_label`: display token such as A001
- `patient_name`: demo patient name
- `department`: selected department
- `status`: Waiting, Serving, Completed, or Cancelled
- `created_at`, `called_at`, `completed_at`: timestamps

To inspect the database, open `queue.db` using a SQLite viewer, such as the SQLite extension in VS Code, or Python's built-in `sqlite3` module.

## Important prototype limitations

- This is an educational demo, not a production hospital system.
- The staff dashboard has no login. Add authentication and role-based authorization before deployment.
- The Flask development server and `debug=True` are for local development only.
- Do not enter real patient information. A real system needs privacy safeguards, secure deployment, access control, audit logs, backups, and applicable legal/compliance review.
- Queue order is first-come, first-served. It does not perform clinical triage. Emergency patients must follow hospital emergency procedures.
- The wait-time estimate uses a fixed five-minute assumption; real wait times vary.
- For multiple counters or departments, token generation and queue logic should be extended.
- For a demo reset, stop the server and delete `queue.db`. It will be recreated on the next start. This deletes all demo records.
