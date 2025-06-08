from flask import Blueprint, current_app, render_template, request, redirect, url_for, session, jsonify, flash
from app.database import get_db_connection
from app.config import SECRET_KEY
from app.qr import delete_patient_qr_code  # (Assuming save_patient_qr_code() is used elsewhere)
from app.email_helpers import send_credentials_email
from app.auth import generate_random_password, hash_password
from psycopg2 import Binary
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
def admin_dashboard():
    """
    Render the administrator dashboard.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Updated query: join delete_requests with patients and clinicians to get names and reason.
    cursor.execute("""
        SELECT dr.request_id,
               dr.patient_id,
               dr.clinician_id AS medic_id,
               dr.request_date,
               dr.status,
               dr.reason,
               pgp_sym_decrypt(p.first_name::bytea, %s) AS patient_first_name,
               pgp_sym_decrypt(p.last_name::bytea, %s) AS patient_last_name,
               pgp_sym_decrypt(c.name::bytea, %s) AS medic_name
        FROM delete_requests dr
        LEFT JOIN patients p ON dr.patient_id = p.patient_id
        LEFT JOIN clinicians c ON dr.clinician_id = c.clinician_id
        WHERE dr.status = 'Pending'
    """, (SECRET_KEY, SECRET_KEY, SECRET_KEY))
    rows = cursor.fetchall()
    delete_requests = [
        {
            "request_id": row[0],
            "patient_id": row[1],
            "medic_id": row[2],
            "request_date": row[3],
            "status": row[4],
            "deletion_reason": row[5],
            "patient_name": (row[6] + " " + row[7]) if row[6] and row[7] else "Unknown",
            "medic_name": row[8] if row[8] else "Unknown"
        }
        for row in rows
    ]
    
    cursor.execute("""
        SELECT clinician_id, pgp_sym_decrypt(name::bytea, %s) AS name,
               pgp_sym_decrypt(email::bytea, %s) AS email
        FROM clinicians
    """, (SECRET_KEY, SECRET_KEY))
    clinicians = cursor.fetchall()
    clinician_list = [{"clinician_id": row[0], "name": row[1], "email": row[2]} for row in clinicians]
    
    cursor.execute("""
        SELECT patient_id, pgp_sym_decrypt(first_name::bytea, %s) AS first_name,
               pgp_sym_decrypt(last_name::bytea, %s) AS last_name
        FROM patients
    """, (SECRET_KEY, SECRET_KEY))
    patients = cursor.fetchall()
    patient_list = [{"patient_id": row[0], "first_name": row[1], "last_name": row[2]} for row in patients]
    
    cursor.close()
    conn.close()
    return render_template('admin_dashboard.html',
                           delete_requests=delete_requests,
                           clinicians=clinician_list,
                           patients=patient_list)


@admin_bp.route('/patient_qr/<int:patient_id>')
def patient_qr(patient_id):
    """
    Display the QR code for a given patient.
    Assumes QR codes are stored in static/qrcodes/ with filename 'patient_<patient_id>.png'.
    """
    qr_filename = f"qrcodes/patient_{patient_id}.png"
    # Go one directory up from current_app.root_path (from app to project root), then into static.
    qr_path = os.path.join(current_app.root_path, "..", "static", qr_filename)
    qr_path = os.path.abspath(qr_path)
    print("Looking for QR file at:", qr_path)
    
    # Debug: List files in the qrcodes directory.
    dir_path = os.path.join(current_app.root_path, "..", "static", "qrcodes")
    try:
        files = os.listdir(dir_path)
        print("Files in qrcodes directory:", files)
    except Exception as e:
        print("Error listing directory:", e)
    
    if not os.path.exists(qr_path):
        return "QR code not found.", 404
    return render_template("patient_qr.html", qr_filename=qr_filename, patient_id=patient_id)

@admin_bp.route('/clinician/<int:clinician_id>')
def clinician_details(clinician_id):
    """
    Render details for a specific clinician.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT clinician_id,
               pgp_sym_decrypt(name::bytea, %s) AS name,
               pgp_sym_decrypt(email::bytea, %s) AS email
        FROM clinicians
        WHERE clinician_id = %s
    """
    cursor.execute(query, (SECRET_KEY, SECRET_KEY, clinician_id))
    clinician = cursor.fetchone()
    if not clinician:
        cursor.close()
        conn.close()
        return "Clinician not found", 404
    clinician_info = {"clinician_id": clinician[0], "name": clinician[1], "email": clinician[2]}
    
    query_patients = """
        SELECT patient_id,
               pgp_sym_decrypt(first_name::bytea, %s) AS first_name,
               pgp_sym_decrypt(last_name::bytea, %s) AS last_name
        FROM patients
        WHERE assigned_to_clinician = %s
    """
    cursor.execute(query_patients, (SECRET_KEY, SECRET_KEY, clinician_id))
    patients_data = cursor.fetchall()
    patient_list = [{"patient_id": row[0], "first_name": row[1], "last_name": row[2]} for row in patients_data]
    
    query_assignable = """
         SELECT patient_id,
                pgp_sym_decrypt(first_name::bytea, %s) AS first_name,
                pgp_sym_decrypt(last_name::bytea, %s) AS last_name
         FROM patients
         WHERE assigned_to_clinician IS NULL OR assigned_to_clinician != %s
         """
    cursor.execute(query_assignable, (SECRET_KEY, SECRET_KEY, clinician_id))
    assignable_data = cursor.fetchall()
    assignable_patients = [{"patient_id": row[0], "first_name": row[1], "last_name": row[2]} for row in assignable_data]
    
    cursor.close()
    conn.close()
    return render_template('clinician_details.html',
                           clinician=clinician_info,
                           patients=patient_list,
                           unassigned_patients=assignable_patients)

@admin_bp.route('/clinician/<int:clinician_id>/remove_patient/<int:patient_id>', methods=['POST'])
def remove_patient(clinician_id, patient_id):
    """
    Remove a patient from a clinician's assignment.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE patients SET assigned_to_clinician = NULL WHERE patient_id = %s", (patient_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin.clinician_details', clinician_id=clinician_id))

@admin_bp.route('/clinician/<int:clinician_id>/assign_patient', methods=['POST'])
def assign_patient(clinician_id):
    """
    Assign a patient to a clinician.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    patient_id = request.form.get('patient_id')
    if not patient_id:
        return redirect(url_for('admin.clinician_details', clinician_id=clinician_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE patients SET assigned_to_clinician = %s WHERE patient_id = %s", (clinician_id, patient_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin.clinician_details', clinician_id=clinician_id))

@admin_bp.route('/delete_clinician/<int:clinician_id>', methods=['POST'])
def delete_clinician(clinician_id):
    """
    Delete a clinician from the database and unassign their patients.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json() or {}
    deletion_reason = data.get('reason')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clinicians WHERE clinician_id = %s", (clinician_id,))
    cursor.execute("UPDATE patients SET assigned_to_clinician = NULL WHERE assigned_to_clinician = %s", (clinician_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Clinician deleted successfully."})

@admin_bp.route('/create_clinician', methods=['GET', 'POST'])
def create_clinician():
    """
    Create a new clinician record.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hospital_id, pgp_sym_decrypt(name::bytea, %s) AS name FROM hospitals", (SECRET_KEY,))
    hospitals = cursor.fetchall()
    hospital_list = [{"hospital_id": row[0], "name": row[1]} for row in hospitals]
    
    if request.method == 'POST':
        name = request.form.get('name')
        hospital_id = request.form.get('hospital_id')
        email = request.form.get('email')
        if not name or not hospital_id or not email:
            error = "All fields are required."
            return render_template('create_clinician.html', error=error, hospitals=hospital_list)
        new_password = generate_random_password()
        password_hash = hash_password(new_password)
        created_by_admin = session.get('user_id')
        query = """
        INSERT INTO clinicians (hospital_id, name, email, created_by_admin, password_hash, temporary_password)
        VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s), %s, %s, TRUE)
        RETURNING clinician_id
        """
        cursor.execute(query, (hospital_id, name, SECRET_KEY, email, SECRET_KEY, created_by_admin, password_hash))
        clinician_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        login_url = os.environ.get('LOGIN_PAGE_URL', "http://localhost:5000/")
        send_credentials_email(email, name, clinician_id, new_password, login_url)
        return render_template('clinician_created.html', password=new_password)
    
    cursor.close()
    conn.close()
    return render_template('create_clinician.html', hospitals=hospital_list)

@admin_bp.route('/process_delete_request/<int:request_id>/<string:action>')
def process_delete_request(request_id, action):
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    if action.lower() not in ['approve', 'disapprove']:
        return "Invalid action", 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM delete_requests WHERE request_id = %s", (request_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        return "Deletion request not found", 404
    patient_id = result[0]
    admin_id = session.get('user_id')
    
    if action.lower() == "approve":
        cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
        delete_patient_qr_code(patient_id)
    new_status = "Approved" if action.lower() == "approve" else "Disapproved"
    cursor.execute("UPDATE delete_requests SET status = %s, admin_id = %s WHERE request_id = %s", (new_status, admin_id, request_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin.admin_dashboard'))

# NEW: Admin Creation Route
@admin_bp.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    """
    Create a new admin account.
    This route is accessible only to logged-in admins.
    """
    if not session.get('user_id') or session.get('user_type') != 'admin':
        return redirect(url_for('auth.login_page'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        hospital_id = request.form.get('hospital_id')  # Optional field
        password = request.form.get('password')
        
        if not name or not password:
            flash("Name and password are required.", "error")
            return render_template('create_admin.html')
        
        password_hash = hash_password(password)
        name_binary = Binary(name.encode('utf-8'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO admins (name, hospital_id, password_hash) VALUES (%s, %s, %s) RETURNING admin_id",
                (name_binary, hospital_id, password_hash)
            )
            new_admin_id = cursor.fetchone()[0]
            conn.commit()
            flash(f"Admin account created successfully! New admin ID: {new_admin_id}", "success")
        except Exception as e:
            conn.rollback()
            flash("Error creating admin account: " + str(e), "error")
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('create_admin.html')
