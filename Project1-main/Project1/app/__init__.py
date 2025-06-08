import os
from flask import Flask
from app.config import SECRET_KEY
from app.routes import register_blueprints
from app.qr import generate_static_qrcodes  # Import the QR code generation function

def create_app():
    """
    Create and configure the Flask application.
    """
    # Get the absolute path to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Create Flask app and explicitly define template and static folder locations
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, 'templates'), 
                static_folder=os.path.join(project_root, 'static'))

    app.secret_key = SECRET_KEY

    # Register Blueprints
    register_blueprints(app)

    # Option A: Generate static QR codes during initialization
    generate_static_qrcodes()

    return app
