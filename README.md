# Attendance & Marks Early-Warning System
Upload attendance + test CSVs. The system flags students near or below 85%, computes
the classes they must attend in a row to recover, flags weak or falling marks, emails
the student (CC teacher and adviser), auto-calls students below 85%, offers booking in
teachers' free slots, shows department- and subject-wise risk, and sends a weekly summary.

Recovery formula: x = ceil((0.85*held - attended) / 0.15)

## Run
pip install -r requirements.txt
streamlit run app.py

## Real emails/calls (optional; dry-run otherwise)
SMTP_USER, SMTP_PASS (Gmail app password); VAPI_KEY, VAPI_ASSISTANT_ID, VAPI_PHONE_ID

## CSV columns
attendance: student_id,name,email,phone,dept,subject,teacher_email,advisor_email,held,attended
marks: student_id,subject,prev_test,latest_test
slots: teacher_email,slot