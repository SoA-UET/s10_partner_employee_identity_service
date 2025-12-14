from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from .collections import Collections
from .services.LoggerService import LoggerService
from .services.JWTService import JWTService
from .services.AuthService import AuthService
from .services.EmployeeService import EmployeeService
from .controllers.v1.partner_employees import (
    auth_bp, employees_bp, jwks_bp, init_controllers
)

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Allow all origins for testing, restrict in production
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    collections = Collections()
    logger = LoggerService()
    
    jwt_service = JWTService(collections.signing_keys, logger)
    
    auth_service = AuthService(
        collections.employees,
        collections.roles,
        jwt_service,
        logger
    )
    
    employee_service = EmployeeService(
        collections.employees,
        collections.roles,
        auth_service,
        logger
    )
    
    init_controllers(auth_service, employee_service, jwt_service, logger)
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(jwks_bp)
    
    @app.route('/')
    def index():
        return {
            "service": "Partner Employee Identity Service (S10)",
            "version": "0.1.0",
            "status": "running"
        }
    
    @app.route('/health')
    def health():
        return {"status": "healthy"}
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '7010'))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Partner Employee Identity Service on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
