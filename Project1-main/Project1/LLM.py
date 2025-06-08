import psycopg2  # PostgreSQL database adapter for Python
from transformers import pipeline  # Hugging Face pipeline for summarization

# ============================
# DATABASE CONFIGURATION
# ============================

DB_CONFIG = {
    "dbname": "Hospital_system",
    "user": "postgres",
    "password": "BrainingAI12345!",
    "host": "localhost",
    "port": "5432"
}

SECRET_KEY = "SuperSecretKey12345!$B7Iol"

# ============================
# FUNCTION: get_patient_info
# ============================

def get_patient_info(patient_id):
    """
    Retrieves and decrypts patient data from the PostgreSQL database.
    Returns a dictionary with patient information or None if not found.
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        patient_id,
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
                    WHERE patient_id = %s
                """
                
                params = (SECRET_KEY,) * 12 + (int(patient_id),)
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    return dict(zip([
                        "patient_id", "disease", "severity", "symptoms", "observations", 
                        "diagnostic_procedure", "lab_values", "vital_health_metrics", "prescriptions", 
                        "dosage", "therapeutic_procedure", "therapy_description", "body_parts", "last_update"
                    ], row))
    except Exception as e:
        print(f"Error fetching patient info: {e}")
    return None

# ============================
# INITIALIZE SUMMARIZATION PIPELINE
# ============================

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# ============================
# FUNCTION: generate_summary
# ============================

def generate_summary(patient_id):
    """
    Generates a structured, detailed medical summary for a patient.
    """
    patient_info = get_patient_info(patient_id)
    if not patient_info:
        return "Patient not found."
    
    prompt = """
    Create a structured and professional medical summary for the following patient.
    
    **Patient Demographics:**
    - Patient ID: {patient_info['patient_id']}
    - Primary Diagnosis: {patient_info['disease']}
    - Severity: {patient_info['severity']}

    **Symptoms & Observations:**
    - Symptoms: {patient_info['symptoms']}
    - Observations: {patient_info['observations']}
    
    **Diagnostic Findings:**
    - Diagnostic Procedures: {patient_info['diagnostic_procedure']}
    - Lab Values: {patient_info['lab_values']}
    - Vital Health Metrics: {patient_info['vital_health_metrics']}
    
    **Treatment & Medications:**
    - Prescriptions: {patient_info['prescriptions']} (Dosage: {patient_info['dosage']})
    - Therapeutic Procedures: {patient_info['therapeutic_procedure']}
    - Therapy Description: {patient_info['therapy_description']}
    
    **Anatomical Considerations:**
    - Affected Body Parts: {patient_info['body_parts']}
    
    **Prognosis & Next Steps:**
    - Last Updated: {patient_info['last_update']}
    
    Provide a detailed, clinical summary in professional language.
    """
    
    summary_output = summarizer(prompt, max_length=500, do_sample=False)
    
    return summary_output[0]['summary_text']

# ============================
# MAIN EXECUTION BLOCK
# ============================

if __name__ == "__main__":
    print("\nGenerated Summary:\n")
    result = generate_summary(1)
    print(result)
