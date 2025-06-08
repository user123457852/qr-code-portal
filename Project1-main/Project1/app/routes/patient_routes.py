# app/routes/patient_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
from app.database import get_db_connection
from app.config import SECRET_KEY
from app.qr import save_patient_qr_code
from LLM import generate_summary

patient_bp = Blueprint('patient', __name__)

def fetch_all_patients():
    """
    Retrieve all patients from the database along with their decrypted data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
           patient_id,
           assigned_to_clinician,
           pgp_sym_decrypt(first_name::bytea, %s) AS first_name,
           pgp_sym_decrypt(last_name::bytea, %s) AS last_name,
           pgp_sym_decrypt(age::bytea, %s) AS age,
           pgp_sym_decrypt(sex::bytea, %s) AS sex,
           pgp_sym_decrypt(gender::bytea, %s) AS gender,
           pgp_sym_decrypt(email::bytea, %s) AS email,
           pgp_sym_decrypt(phone_number::bytea, %s) AS phone_number,
           pgp_sym_decrypt(disease::bytea, %s) AS disease,
           pgp_sym_decrypt(severity::bytea, %s) AS severity,
           pgp_sym_decrypt(symptoms::bytea, %s) AS symptoms,
           pgp_sym_decrypt(observations::bytea, %s) AS observations,
           pgp_sym_decrypt(diagnostic_procedure::bytea, %s) AS diagnostic_procedure,
           pgp_sym_decrypt(lab_values::bytea, %s) AS lab_values,
           pgp_sym_decrypt(vital_health_metrics::bytea, %s) AS vital_health_metrics,
           pgp_sym_decrypt(prescriptions::bytea, %s) AS prescriptions,
           pgp_sym_decrypt(dosage::bytea, %s) AS dosage,
           pgp_sym_decrypt(therapeutic_procedure::bytea, %s) AS therapeutic_procedure,
           pgp_sym_decrypt(therapy_description::bytea, %s) AS therapy_description,
           pgp_sym_decrypt(body_parts::bytea, %s) AS body_parts,
           last_update
        FROM patients
    """
    params = (SECRET_KEY,) * 19
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

@patient_bp.route('/patient_info')
def patient_info():
    """
    Render the patient information page for the logged-in clinician.
    If the clinician has no patients, render a custom "Access Denied" page.
    """
    if not session.get('user_id') or session.get('user_type') != 'clinician':
        return redirect(url_for('auth.login_page'))
    
    clinician_id = int(session.get('user_id'))
    qr_patient_id = session.get('patient_id')
    all_patients = fetch_all_patients()
    
    clinician_patients = []
    clinician_patient_ids = []
    
    for row in all_patients:
        if row[1] == clinician_id:
            patient_data = {
                "patient_id": row[0],
                "first_name": row[2],
                "last_name": row[3],
                "age": row[4],
                "sex": row[5],
                "gender": row[6],
                "email": row[7],
                "phone_number": row[8],
                "disease": row[9],
                "severity": row[10],
                "symptoms": row[11],
                "observations": row[12],
                "diagnostic_procedure": row[13],
                "lab_values": row[14],
                "vital_health_metrics": row[15],
                "prescriptions": row[16],
                "dosage": row[17],
                "therapeutic_procedure": row[18],
                "therapy_description": row[19],
                "body_parts": row[20],
                "last_update": row[21]
            }
            clinician_patients.append(patient_data)
            clinician_patient_ids.append(row[0])
    
    # If no patients found, render the custom access denied page.
    if not clinician_patients:
        return render_template('no_patient.html')
    
    # Optionally, if a patient is requested via QR and it is not among the clinician's patients.
    if qr_patient_id and int(qr_patient_id) not in clinician_patient_ids:
        return redirect(url_for('patient.no_permission'))
    
    if qr_patient_id:
        llm_summary = generate_summary(int(qr_patient_id))
    else:
        llm_summary = "No patient selected."
    
    return render_template('patient_info.html', patients=clinician_patients, llm_summary=llm_summary)

@patient_bp.route('/no_permission')
def no_permission():
    """
    Render a page indicating the clinician does not have permission to view the requested patient.
    """
    return render_template('no_permission.html')

@patient_bp.route('/update_patient/<int:patient_id>', methods=['POST', 'GET'])
def update_patient_route(patient_id):
    """
    Update an existing patient's record with new data (POST).
    If GET, just return a message or the patient's details.
    """
    if request.method == 'POST':
        # 1) Get the JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # 2) Extract fields from the incoming data
        #    (Make sure these match the keys you send from the frontend)
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        age = data.get("age", "")
        sex = data.get("sex", "")
        gender = data.get("gender", "")
        email = data.get("email", "")
        phone_number = data.get("phone_number", "")
        disease = data.get("disease", "")
        severity = data.get("severity", "")
        symptoms = data.get("symptoms", "")
        diagnostic_procedure = data.get("diagnostic_procedure", "")
        lab_values = data.get("lab_values", "")
        prescriptions = data.get("prescriptions", "")
        dosage = data.get("dosage", "")
        therapeutic_procedure = data.get("therapeutic_procedure", "")
        therapy_description = data.get("therapy_description", "")
        body_parts = data.get("body_parts", "")

        # For good measure, update "last_update" to current timestamp
        last_update_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3) Build the UPDATE query using pgp_sym_encrypt for each field
        update_query = """
            UPDATE patients
            SET
                first_name = pgp_sym_encrypt(%s, %s),
                last_name = pgp_sym_encrypt(%s, %s),
                age = pgp_sym_encrypt(%s, %s),
                sex = pgp_sym_encrypt(%s, %s),
                gender = pgp_sym_encrypt(%s, %s),
                email = pgp_sym_encrypt(%s, %s),
                phone_number = pgp_sym_encrypt(%s, %s),
                disease = pgp_sym_encrypt(%s, %s),
                severity = pgp_sym_encrypt(%s, %s),
                symptoms = pgp_sym_encrypt(%s, %s),
                diagnostic_procedure = pgp_sym_encrypt(%s, %s),
                lab_values = pgp_sym_encrypt(%s, %s),
                prescriptions = pgp_sym_encrypt(%s, %s),
                dosage = pgp_sym_encrypt(%s, %s),
                therapeutic_procedure = pgp_sym_encrypt(%s, %s),
                therapy_description = pgp_sym_encrypt(%s, %s),
                body_parts = pgp_sym_encrypt(%s, %s),
                last_update = %s
            WHERE patient_id = %s
        """

        # 4) Prepare the parameter tuple (matching the query order)
        update_params = (
            first_name, SECRET_KEY,
            last_name, SECRET_KEY,
            age, SECRET_KEY,
            sex, SECRET_KEY,
            gender, SECRET_KEY,
            email, SECRET_KEY,
            phone_number, SECRET_KEY,
            disease, SECRET_KEY,
            severity, SECRET_KEY,
            symptoms, SECRET_KEY,
            diagnostic_procedure, SECRET_KEY,
            lab_values, SECRET_KEY,
            prescriptions, SECRET_KEY,
            dosage, SECRET_KEY,
            therapeutic_procedure, SECRET_KEY,
            therapy_description, SECRET_KEY,
            body_parts, SECRET_KEY,
            last_update_val,
            patient_id
        )

        # 5) Execute the update in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(update_query, update_params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({"error": str(e)}), 500
        cursor.close()
        conn.close()

        # 6) Return success response
        return jsonify({
            "message": f"Patient {patient_id} updated successfully!",
            "data": data
        })

    # For GET requests (optional), just show a placeholder message
    return jsonify({"message": f"Displaying details for patient {patient_id}"})

@patient_bp.route('/patient_details/<int:patient_id>')
def patient_details(patient_id):
    """
    Render detailed information for a specific patient.
    """
    if not session.get('user_id'):
        return redirect(url_for('auth.login_page'))
    patients = fetch_all_patients()
    patient_data = None
    for row in patients:
        if row[0] == patient_id:
            patient_data = {
                "patient_id": row[0],
                "first_name": row[2],
                "last_name": row[3],
                "age": row[4],
                "sex": row[5],
                "gender": row[6],
                "email": row[7],
                "phone_number": row[8],
                "disease": row[9],
                "severity": row[10],
                "symptoms": row[11],
                "observations": row[12],
                "diagnostic_procedure": row[13],
                "lab_values": row[14],
                "vital_health_metrics": row[15],
                "prescriptions": row[16],
                "dosage": row[17],
                "therapeutic_procedure": row[18],
                "therapy_description": row[19],
                "body_parts": row[20],
                "last_update": row[21],
                "assigned_to_clinician": row[1]
            }
            break
    if not patient_data:
        return jsonify({"error": "Patient not found."}), 404
    llm_summary = generate_summary(patient_id)
    return render_template('patient_info.html', patients=[patient_data], llm_summary=llm_summary)

@patient_bp.route('/create_basic_patient', methods=['GET', 'POST'])
def create_basic_patient():
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))

    if request.method == 'POST':
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        age = request.form.get("age")
        sex = request.form.get("sex")
        assigned_clinician = request.form.get("assigned_clinician")

        empty_value = ''
        last_update_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO patients (
                first_name, last_name, age, sex, gender, email, phone_number,
                disease, severity, symptoms, observations, diagnostic_procedure,
                lab_values, vital_health_metrics, prescriptions, dosage,
                therapeutic_procedure, therapy_description, body_parts, last_update, assigned_to_clinician
            ) VALUES (
                pgp_sym_encrypt(%s, %s),  -- first_name
                pgp_sym_encrypt(%s, %s),  -- last_name
                pgp_sym_encrypt(%s, %s),  -- age
                pgp_sym_encrypt(%s, %s),  -- sex
                pgp_sym_encrypt(%s, %s),  -- gender
                pgp_sym_encrypt(%s, %s),  -- email
                pgp_sym_encrypt(%s, %s),  -- phone_number
                pgp_sym_encrypt(%s, %s),  -- disease
                pgp_sym_encrypt(%s, %s),  -- severity
                pgp_sym_encrypt(%s, %s),  -- symptoms
                pgp_sym_encrypt(%s, %s),  -- observations
                pgp_sym_encrypt(%s, %s),  -- diagnostic_procedure
                pgp_sym_encrypt(%s, %s),  -- lab_values
                pgp_sym_encrypt(%s, %s),  -- vital_health_metrics
                pgp_sym_encrypt(%s, %s),  -- prescriptions
                pgp_sym_encrypt(%s, %s),  -- dosage
                pgp_sym_encrypt(%s, %s),  -- therapeutic_procedure
                pgp_sym_encrypt(%s, %s),  -- therapy_description
                pgp_sym_encrypt(%s, %s),  -- body_parts
                %s,                    -- last_update (plain text)
                %s                     -- assigned_to_clinician (plain text)
            ) RETURNING patient_id
        """

        params = (
            first_name, SECRET_KEY,              # first_name
            last_name, SECRET_KEY,               # last_name
            age, SECRET_KEY,                     # age
            sex, SECRET_KEY,                     # sex
            empty_value, SECRET_KEY,             # gender
            empty_value, SECRET_KEY,             # email
            empty_value, SECRET_KEY,             # phone_number
            empty_value, SECRET_KEY,             # disease
            empty_value, SECRET_KEY,             # severity
            empty_value, SECRET_KEY,             # symptoms
            empty_value, SECRET_KEY,             # observations
            empty_value, SECRET_KEY,             # diagnostic_procedure
            empty_value, SECRET_KEY,             # lab_values
            empty_value, SECRET_KEY,             # vital_health_metrics
            empty_value, SECRET_KEY,             # prescriptions
            empty_value, SECRET_KEY,             # dosage
            empty_value, SECRET_KEY,             # therapeutic_procedure
            empty_value, SECRET_KEY,             # therapy_description
            empty_value, SECRET_KEY,             # body_parts
            last_update_val,                     # last_update (plain)
            assigned_clinician                   # assigned_to_clinician (plain)
        )

        print("Parameters count:", len(params))  # Expected output: 40

        try:
            cursor.execute(query, params)
            result = cursor.fetchone()
            print("Query result:", result)

            if not result or len(result) < 1:
                conn.rollback()
                cursor.close()
                conn.close()
                print("Error: No patient_id returned from INSERT.")
                return "Error: Patient could not be created.", 500

            new_patient_id = result[0]
            conn.commit()

            save_patient_qr_code(new_patient_id)

            cursor.close()
            conn.close()

            return redirect(url_for('admin.admin_dashboard'))

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print("Database Error:", e)
            return f"Database error: {e}", 500

    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT clinician_id, pgp_sym_decrypt(name::bytea, %s) AS name
            FROM clinicians
        """, (SECRET_KEY,))
        clinicians = cursor.fetchall()
        clinician_list = [{"clinician_id": row[0], "name": row[1]} for row in clinicians]
        cursor.close()
        conn.close()
        return render_template('create_basic_patient.html', clinicians=clinician_list)

@patient_bp.route('/add_patient', methods=['GET', 'POST'])
def add_patient_route():
    """
    Add a new patient record via the web interface.
    """
    if not session.get('user_id'):
        return redirect(url_for('auth.login_page'))
    if request.method == 'POST':
        data = {
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
            "age": request.form.get("age"),
            "sex": request.form.get("sex"),
            "disease": request.form.get("disease"),
            "prescriptions": request.form.get("prescriptions"),
        }
        empty_value = ''
        last_update_val = request.form.get("last_update") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        assigned_to_clinician = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO patients (
                first_name, last_name, age, sex, gender, email, phone_number,
                disease, severity, symptoms, observations, diagnostic_procedure,
                lab_values, vital_health_metrics, prescriptions, dosage,
                therapeutic_procedure, therapy_description, body_parts, last_update, assigned_to_clinician
            ) VALUES (
                pgp_sym_encrypt(%s, %s),
                pgp_sym_encrypt(%s, %s),
                pgp_sym_encrypt(%s, %s),
                pgp_sym_encrypt(%s, %s),
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),  
                pgp_sym_encrypt(%s, %s),
                pgp_sym_encrypt(%s, %s),
                %s,
                %s
            ) RETURNING patient_id
        """
        params = (
            data["first_name"], SECRET_KEY,
            data["last_name"], SECRET_KEY,
            data["age"], SECRET_KEY,
            data["sex"], SECRET_KEY,
            empty_value, SECRET_KEY,
            empty_value, SECRET_KEY,
            empty_value, SECRET_KEY,
            data["disease"], SECRET_KEY,
            empty_value, SECRET_KEY,
            empty_value, SECRET_KEY,
            empty_value, SECRET_KEY,
            data["prescriptions"], SECRET_KEY,
            empty_value, SECRET_KEY,
            empty_value, SECRET_KEY,
            empty_value, SECRET_KEY,
            last_update_val,
            assigned_to_clinician
        )
        cursor.execute(query, params)
        new_patient_id = cursor.fetchone()[0]
        conn.commit()
        save_patient_qr_code(new_patient_id)
        cursor.close()
        conn.close()
        return redirect(url_for('patient.patient_info'))
    return render_template('add_patient.html')

# ------------------------------
# New Route: Deletion Request
# ------------------------------
@patient_bp.route('/request_delete_patient/<int:patient_id>', methods=['POST'])
def request_delete_patient(patient_id):
    data = request.get_json()
    reason = data.get("reason")
    if not reason:
        return jsonify({"success": False, "error": "Please provide a reason"}), 400

    # Get the clinician's id from the session (since they're making the request)
    clinician_id = session.get('user_id')
    status = "Pending"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO delete_requests (patient_id, clinician_id, admin_id, request_date, status, reason)
            VALUES (%s, %s, NULL, NOW(), %s, %s)
        """
        cursor.execute(query, (patient_id, clinician_id, status, reason))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Deletion request submitted successfully."})


