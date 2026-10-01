# 🫀 HeartAI: Heart Attack Risk Prediction & Clinical Decision Support System

> **An End-to-End Clinical Decision Support System (CDSS) for Cardiovascular Risk Assessment**

HeartAI is a web-based Clinical Decision Support System designed to assist healthcare professionals in evaluating heart attack risks[cite: 8]. By leveraging machine learning models and data mining techniques, the system analyzes patient demographics, medical metrics, and lifestyle factors to deliver instant risk assessments, actionable insights, personalized dietary recommendations, and patient management features[cite: 8, 140, 142].

*Developed as a Bachelor's Thesis Project for Üsküdar University, Department of Computer Engineering[cite: 1].*

---

## 📌 About the Project

HeartAI addresses critical challenges in modern healthcare by integrating predictive machine learning with daily clinical workflows[cite: 8]. Key capabilities include:

* **Machine Learning Risk Engine:** Predicts heart attack risk percentages (%) and categories (Low, Medium, High) based on clinical indicators such as age, average glucose levels, BMI, hypertension, and smoking status[cite: 8, 140].
* **Relational Database Architecture:** Built on SQLite to handle structured tables including `users`, `predictions`, `appointments`, `procedures`, `patient_files`, and `diet_plans`.
* **Clinical Safety & Visual Alerts:** Features real-time visual and audio warnings for patients identified in high-risk categories[cite: 8, 140].
* **Personalized Nutrition Engine:** Automatically generates tailored dietary protocols based on calculated risk scores and blood sugar levels[cite: 8, 140].
* **Patient Management & Archiving:** Supports medical file uploads (`.pdf`, `.jpg`, `.png`), medical prescription creation, and procedure tracking[cite: 8, 140].
* **Automated PDF Reports:** Uses FPDF to generate official, downloadable risk assessment reports[cite: 8, 140].
* **Waiting Room Display (TV Mode):** Provides a public queue broadcast view for clinical waiting areas[cite: 8, 140].

---

## 📁 Directory Structure

```text
.
├── app.py                         # Main Flask backend server, routes, and DB initialization[cite: 8, 12, 140]
├── model_egitimi_v2.py            # Machine learning model training and preprocessing script[cite: 142]
├── healthcare-dataset-stroke-data.csv # Clinical dataset used for model training[cite: 35, 142]
├── database.db                    # SQLite database instance[cite: 8, 140, 141]
├── model/                         # Trained machine learning artifacts
│   ├── model.pkl                  # Trained Random Forest / Classifier model[cite: 140, 142]
│   ├── scaler.pkl                 # StandardScaler object[cite: 140, 142]
│   └── encoders.pkl               # LabelEncoders for categorical variables[cite: 140, 142]
├── uploads/                       # Storage folder for patient medical files/tests
├── templates/                     # Jinja2 HTML View Templates[cite: 140]
│   ├── login.html                 # Authentication and registration interface[cite: 140]
│   ├── dashboard.html             # Analytics and statistical overview panel[cite: 8, 140]
│   ├── patients.html              # Patient list management interface[cite: 8, 140]
│   ├── new_patient.html           # New patient registration & instant risk analysis[cite: 8, 140]
│   ├── patient_detail.html        # Patient history, file management, and prescription hub[cite: 8, 140]
│   ├── history.html               # Prediction log and historical records[cite: 140]
│   ├── appointments.html          # Appointment scheduling module[cite: 8, 140]
│   ├── create_procedure.html      # Form to define new clinical procedures[cite: 8, 140]
│   ├── all_procedures.html        # Procedures log & financial summaries[cite: 8, 140]
│   ├── diet_selection.html        # Patient selection interface for dietary plans[cite: 8, 140]
│   ├── diet_plan.html             # Personalized medical diet protocol display[cite: 8, 140]
│   ├── waiting_room.html          # Waiting room TV queue interface[cite: 8, 140]
│   └── monitor.html               # Real-time patient vital sign simulation panel[cite: 8, 140]
└── static/                        # CSS stylesheets, JS scripts, and static media
