🏥 Doctor Appointment System

A simple backend app that lets patients book appointments with doctors online.

What does it do?
Patients sign up, browse doctors, and book an appointment.
Doctors set their working hours, then accept or reject requests.
After the visit, the doctor writes the diagnosis and prescription, and the patient can read it.
Rules built into the system
No double booking for the same time.
No booking in the past or outside the doctor’s working hours.
Each user only sees their own data.
Built with

Python, Django, Django REST Framework, JWT login, and Docker.

How to run it

git clone <your-repo-link>
cd <project-folder>
docker build -t doctor-appointments .
docker run -p 8000:8000 doctor-appointments

Then open: http://localhost:8000/
