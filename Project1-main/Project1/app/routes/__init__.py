# app/routes/__init__.py
from flask import Blueprint

from app.routes import auth_routes, patient_routes, admin_routes, api_routes

def register_blueprints(app):
    """
    Register all blueprints for the application.
    """
    app.register_blueprint(auth_routes.auth_bp)
    app.register_blueprint(patient_routes.patient_bp)
    app.register_blueprint(admin_routes.admin_bp, url_prefix='/admin')
    app.register_blueprint(api_routes.api_bp)