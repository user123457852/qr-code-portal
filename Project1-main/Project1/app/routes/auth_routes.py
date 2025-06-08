# app/routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, timedelta
import random, jwt, os

from app.database import get_db_connection
from app.config import SECRET_KEY, LOGIN_PAGE_URL
from app.auth import verify_password, hash_password, generate_random_password, login_user
from app.email_helpers import send_email, send_credentials_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET'], endpoint='login_page')
def login_page():
    """
    Render the login page.
    If a 'patient_id' is provided in the query string, store it in the session.
    """
    patient_id = request.args.get('patient_id')
    if patient_id:
        session['patient_id'] = patient_id
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login_post():
    """
    Process login submissions for both admins and clinicians.
    """
    user_id = request.form['userInput']
    password = request.form['passwordInput']
    try:
        numeric_id = int(user_id)
    except ValueError:
        return render_template('login.html', error_message="User ID must be numeric.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Try to find an admin with this ID first.
    cursor.execute(
        "SELECT password_hash FROM admins WHERE admin_id = %s",
        (numeric_id,)
    )
    admin_result = cursor.fetchone()
    if admin_result:
        stored_hash = admin_result[0]
        if verify_password(password, stored_hash):
            session['user_id'] = numeric_id
            session['user_type'] = "admin"
            cursor.close()
            conn.close()
            # Redirect to the admin dashboard (adjust the endpoint as needed)
            return redirect(url_for('admin.admin_dashboard'))
        else:
            cursor.close()
            conn.close()
            return render_template('login.html', error_message="Invalid credentials. Try again.")

    # If not an admin, check the clinicians table.
    cursor.execute(
        "SELECT password_hash, temporary_password, has_logged_in, pgp_sym_decrypt(email::bytea, %s) as email "
        "FROM clinicians WHERE clinician_id = %s",
        (SECRET_KEY, numeric_id)
    )
    result = cursor.fetchone()
    if result:
        stored_hash, temp_password, has_logged_in, email = result
        if verify_password(password, stored_hash):
            session['user_id'] = numeric_id
            session['user_type'] = "clinician"
            if temp_password:
                cursor.close()
                conn.close()
                return redirect(url_for('auth.update_password'))
            if not has_logged_in:
                cursor.execute("UPDATE clinicians SET has_logged_in = TRUE WHERE clinician_id = %s", (numeric_id,))
                conn.commit()
                cursor.close()
                conn.close()
                return redirect(url_for('patient.patient_info'))
            if isinstance(email, (bytes, memoryview)):
                email = email.tobytes().decode('utf-8', errors='replace') if isinstance(email, memoryview) else email.decode('utf-8', errors='replace')
            verification_code = str(random.randint(10000, 99999))
            session['verification_code'] = verification_code
            session['clinician_id'] = numeric_id
            send_email(email, "Your Login Verification Code", f"Your verification code is: {verification_code}")
            cursor.close()
            conn.close()
            return redirect(url_for('auth.verify_code'))
    cursor.close()
    conn.close()
    return render_template('login.html', error_message="Invalid credentials. Try again.")

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """
    Handle the "forgot password" functionality.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash("Email is required.", "danger")
            return render_template('forgot_password.html')
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT clinician_id FROM clinicians WHERE pgp_sym_decrypt(email::bytea, %s) = %s"
        cursor.execute(query, (SECRET_KEY, email))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            clinician_id = result[0]
            token = jwt.encode({
                "clinician_id": clinician_id,
                "exp": datetime.utcnow() + timedelta(hours=1)
            }, SECRET_KEY, algorithm="HS256")
            reset_link = f"{LOGIN_PAGE_URL}reset_password/{token}"
            subject = "Password Reset Request"
            body = (
                f"Dear User,\n\n"
                f"To reset your password, please click the following link: {reset_link}\n"
                "This link will expire in 1 hour.\n\n"
                "If you did not request a password reset, please ignore this email."
            )
            send_email(email, subject, body)
            flash("Password reset instructions have been sent to your email.", "success")
        else:
            flash("No account found with that email.", "danger")
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Handle password resets using a JWT token.
    """
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        clinician_id = data["clinician_id"]
    except jwt.ExpiredSignatureError:
        return "The reset link has expired.", 400
    except jwt.InvalidTokenError:
        return "Invalid reset token.", 400

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password != confirm_password:
            return render_template('reset_password.html', error="Passwords do not match.", token=token)
        new_hashed = hash_password(new_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE clinicians SET password_hash = %s, temporary_password = FALSE WHERE clinician_id = %s"
        cursor.execute(query, (new_hashed, clinician_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('auth.password_changed'))
    return render_template('reset_password.html', token=token)

@auth_bp.route('/update_password', methods=['GET', 'POST'])
def update_password():
    """
    Allow clinicians to update their password.
    """
    if not session.get('user_id') or session.get('user_type') != 'clinician':
        return redirect(url_for('auth.login_page'))
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password != confirm_password:
            return render_template('update_password.html', error_message="Passwords do not match.")
        new_hashed = hash_password(new_password)
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE clinicians SET password_hash = %s, temporary_password = FALSE, has_logged_in = TRUE WHERE clinician_id = %s"
        cursor.execute(query, (new_hashed, session.get('user_id')))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('patient.patient_info'))
    return render_template('update_password.html')

@auth_bp.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    """
    Endpoint for verifying the 2FA code.
    """
    if request.method == 'POST':
        entered_code = request.form.get('code')
        if entered_code == session.get('verification_code'):
            session.pop('verification_code', None)
            if 'patient_id' in session:
                patient_id = session.pop('patient_id')
                return redirect(url_for('patient.patient_details', patient_id=patient_id))
            else:
                return redirect(url_for('patient.patient_info'))
        else:
            return render_template('verify_code.html', error="Invalid verification code. Please try again.")
    return render_template('verify_code.html')

@auth_bp.route('/resend_code', methods=['GET'])
def resend_code():
    """
    Resend a new 2FA verification code to the clinician.
    """
    clinician_id = session.get('clinician_id')
    if not clinician_id:
        return redirect(url_for('auth.login_page'))
    new_code = str(random.randint(10000, 99999))
    session['verification_code'] = new_code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pgp_sym_decrypt(email::bytea, %s) as email FROM clinicians WHERE clinician_id = %s",
        (SECRET_KEY, clinician_id)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if not result:
        return jsonify({"error": "Clinician not found"}), 404
    email = result[0]
    if isinstance(email, (bytes, memoryview)):
        email = email.tobytes().decode('utf-8', errors='replace') if isinstance(email, memoryview) else email.decode('utf-8', errors='replace')
    send_email(email, "Your New Login Verification Code", f"Your new verification code is: {new_code}")
    return jsonify({"message": "New verification code sent."})

@auth_bp.route('/scan_qr/<int:clinician_id>', methods=['GET'])
def scan_qr(clinician_id):
    """
    Endpoint invoked when a clinician scans a QR code.
    """
    patient_id = request.args.get('patient_id')
    if patient_id:
        session['patient_id'] = patient_id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pgp_sym_decrypt(email::bytea, %s) as email, has_logged_in FROM clinicians WHERE clinician_id = %s",
        (SECRET_KEY, clinician_id)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if not result:
        return jsonify({'error': 'Clinician not found'}), 404
    email, has_logged_in = result
    if isinstance(email, (bytes, memoryview)):
        email = email.tobytes().decode('utf-8', errors='replace') if isinstance(email, memoryview) else email.decode('utf-8', errors='replace')
    if not email.strip():
        return jsonify({'error': 'Clinician email is empty. Please update your email information.'}), 400
    if has_logged_in:
        verification_code = str(random.randint(10000, 99999))
        session['verification_code'] = verification_code
        session['clinician_id'] = clinician_id
        send_email(email, "Your Login Verification Code", f"Your verification code is: {verification_code}")
        return redirect(url_for('auth.verify_code'))
    else:
        return redirect(url_for('auth.login_page'))

@auth_bp.route('/password_changed')
def password_changed():
    """
    Render the confirmation page after a successful password change.
    """
    return render_template('password_changed.html')
