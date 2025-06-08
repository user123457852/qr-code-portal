# app/routes/api_routes.py
from flask import Blueprint, request, jsonify, session, redirect, url_for
from marshmallow import Schema, fields, ValidationError
from app.database import get_db_connection
from app.config import SECRET_KEY
from app.auth import login_user
from app.qr import save_patient_qr_code

api_bp = Blueprint('api', __name__, url_prefix='/api')

class APILoginSchema(Schema):
    """
    Schema for validating API login requests.
    """
    user_id = fields.Int(required=True)
    password = fields.Str(required=True)
    user_type = fields.Str(required=True, validate=lambda x: x in ['admin', 'clinician'])

class APIPatientSchema(Schema):
    """
    Schema for validating API patient data.
    """
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    age = fields.Int(required=True)
    sex = fields.Str(required=True)
    disease = fields.Str(required=True)
    prescriptions = fields.Str(required=True)

@api_bp.route('/login', methods=['POST'])
def api_login():
    """
    API endpoint for logging in a user.
    """
    try:
        data = APILoginSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    if login_user(data['user_id'], data['password'], data['user_type']):
        session['user_id'] = data['user_id']
        session['user_type'] = data['user_type']
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"}), 401

@api_bp.route('/patients', methods=['GET'])
def api_get_patients():
    """
    API endpoint to retrieve all patients.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id, pgp_sym_decrypt(first_name::bytea, %s) AS first_name, pgp_sym_decrypt(last_name::bytea, %s) AS last_name FROM patients", (SECRET_KEY, SECRET_KEY))
    patients = cursor.fetchall()
    cursor.close()
    conn.close()
    result = [{"patient_id": p[0], "first_name": p[1], "last_name": p[2]} for p in patients]
    return jsonify(result)

@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
def api_get_patient(patient_id):
    """
    API endpoint to retrieve a specific patient's details by ID.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT patient_id,
           pgp_sym_decrypt(first_name::bytea, %s) AS first_name,
           pgp_sym_decrypt(last_name::bytea, %s) AS last_name,
           pgp_sym_decrypt(age::bytea, %s) AS age,
           pgp_sym_decrypt(sex::bytea, %s) AS sex,
           pgp_sym_decrypt(disease::bytea, %s) AS disease,
           pgp_sym_decrypt(prescriptions::bytea, %s) AS prescriptions
    FROM patients WHERE patient_id = %s
    """
    params = (SECRET_KEY, SECRET_KEY, SECRET_KEY, SECRET_KEY, SECRET_KEY, SECRET_KEY, patient_id)
    cursor.execute(query, params)
    patient = cursor.fetchone()
    cursor.close()
    conn.close()
    if patient:
        return jsonify({
            "patient_id": patient[0],
            "first_name": patient[1],
            "last_name": patient[2],
            "age": patient[3],
            "sex": patient[4],
            "disease": patient[5],
            "prescriptions": patient[6]
        })
    return jsonify({"error": "Patient not found"}), 404

@api_bp.route('/patients', methods=['POST'])
def api_add_patient():
    """
    API endpoint to add a new patient.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        data = APIPatientSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO patients (first_name, last_name, age, sex, disease, prescriptions)
    VALUES (
        pgp_sym_encrypt(%s, %s),
        pgp_sym_encrypt(%s, %s),
        pgp_sym_encrypt(%s, %s),
        pgp_sym_encrypt(%s, %s),
        pgp_sym_encrypt(%s, %s),
        pgp_sym_encrypt(%s, %s)
    ) RETURNING patient_id
    """
    params = (
        data['first_name'], SECRET_KEY,
        data['last_name'], SECRET_KEY,
        data['age'], SECRET_KEY,
        data['sex'], SECRET_KEY,
        data['disease'], SECRET_KEY,
        data['prescriptions'], SECRET_KEY
    )
    cursor.execute(query, params)
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    save_patient_qr_code(new_id)
    return jsonify({"message": "Patient added", "patient_id": new_id}), 201

@api_bp.route('/patients/<int:patient_id>', methods=['PUT'])
def api_update_patient(patient_id):
    """
    API endpoint to update an existing patient's information.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        data = APIPatientSchema().load(request.json)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    UPDATE patients SET
        first_name = pgp_sym_encrypt(%s, %s),
        last_name = pgp_sym_encrypt(%s, %s),
        age = pgp_sym_encrypt(%s, %s),
        sex = pgp_sym_encrypt(%s, %s),
        disease = pgp_sym_encrypt(%s, %s),
        prescriptions = pgp_sym_encrypt(%s, %s)
    WHERE patient_id = %s
    """
    params = (
        data['first_name'], SECRET_KEY,
        data['last_name'], SECRET_KEY,
        data['age'], SECRET_KEY,
        data['sex'], SECRET_KEY,
        data['disease'], SECRET_KEY,
        data['prescriptions'], SECRET_KEY,
        patient_id
    )
    cursor.execute(query, params)
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Patient updated"})

@api_bp.route('/patients/<int:patient_id>', methods=['DELETE'])
def api_delete_patient(patient_id):
    """
    API endpoint to delete a patient.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Patient deleted"})
