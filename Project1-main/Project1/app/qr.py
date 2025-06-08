# app/qr.py
import qrcode
from io import BytesIO
import os
from app.config import LOGIN_PAGE_URL

def generate_qr_code():
    """
    Generate a QR code for the login page.
    
    Returns:
        BytesIO: An in-memory PNG image of the QR code.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(LOGIN_PAGE_URL)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return img_buffer

def generate_patient_qr_code(patient_id):
    """
    Generate a QR code for a specific patient.
    The URL encodes the patient_id as a query parameter.
    """
    url = f"{LOGIN_PAGE_URL}?patient_id={patient_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return img_buffer

def generate_static_qrcodes():
    """
    Generate and save a static QR code for the login page to a file.
    """
    qr_dir = os.path.join(os.getcwd(), 'static', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, "login_qr.png")
    if not os.path.exists(qr_path):
        qr_img = generate_qr_code()
        with open(qr_path, 'wb') as f:
            f.write(qr_img.getbuffer())
        print(f"Login QR code saved at {qr_path}")

def get_patient_qr_path(patient_id: int) -> str:
    """
    Get the filesystem path for a patient's QR code image.
    """
    qr_dir = os.path.join(os.getcwd(), 'static', 'qrcodes')
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)
    return os.path.join(qr_dir, f"patient_{patient_id}.png")

def save_patient_qr_code(patient_id: int):
    """
    Generate and save a QR code for a specific patient.
    """
    qr_img = generate_patient_qr_code(patient_id)
    path = get_patient_qr_path(patient_id)
    with open(path, "wb") as f:
        f.write(qr_img.getbuffer())
    print(f"Saved QR code for patient {patient_id} at {path}")
    return path

def delete_patient_qr_code(patient_id: int):
    """
    Delete a patient's QR code image from the filesystem.
    """
    path = get_patient_qr_path(patient_id)
    if os.path.exists(path):
        os.remove(path)
        print(f"Deleted QR code for patient {patient_id} from {path}")
