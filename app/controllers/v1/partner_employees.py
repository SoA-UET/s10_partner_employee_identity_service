from flask import Blueprint, request, jsonify
from functools import wraps
import jwt

auth_bp = Blueprint('auth', __name__)
employees_bp = Blueprint('employees', __name__)
jwks_bp = Blueprint('jwks', __name__)

auth_service = None
employee_service = None
jwt_service = None
logger = None

def init_controllers(auth_svc, employee_svc, jwt_svc, logger_svc):
    global auth_service, employee_service, jwt_service, logger
    auth_service = auth_svc
    employee_service = employee_svc
    jwt_service = jwt_svc
    logger = logger_svc

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                "status": "error",
                "error_code": "UNAUTHORIZED",
                "message": "Token không hợp lệ"
            }), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt_service.verify_token(token)
            request.user = payload
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({
                "status": "error",
                "error_code": "TOKEN_EXPIRED",
                "message": "Token đã hết hạn"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "status": "error",
                "error_code": "INVALID_TOKEN",
                "message": "Token không hợp lệ"
            }), 401
    
    return decorated_function

@auth_bp.route('/api/v1/partner-auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "error_code": "INVALID_REQUEST",
            "message": "Dữ liệu không hợp lệ"
        }), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            "status": "error",
            "error_code": "MISSING_FIELDS",
            "message": "Thiếu tên đăng nhập hoặc mật khẩu"
        }), 400
    
    result = auth_service.login(username, password)
    
    if result.get('error'):
        status_code = 403 if result['error'] == 'ACCOUNT_LOCKED' else 401
        return jsonify({
            "status": "error",
            "error_code": result['error'],
            "message": result['message']
        }), status_code
    
    return jsonify(result), 200

@employees_bp.route('/api/v1/partner-employees', methods=['GET'])
@require_auth
def get_all_employees():
    """Get all employees with pagination"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    status = request.args.get('status')
    
    result = employee_service.get_all_employees(page=page, limit=limit, status=status)
    
    # Convert ObjectIds to strings
    for emp in result['employees']:
        emp['_id'] = str(emp['_id'])
        emp['role_id'] = str(emp['role_id'])
    
    return jsonify({
        "status": "success",
        "data": result
    }), 200

@employees_bp.route('/api/v1/partner-employees/<employee_id>', methods=['GET'])
@require_auth
def get_employee_detail(employee_id):
    """Get employee detail with roles and permissions"""
    result = employee_service.get_employee_detail(employee_id)
    
    if result.get('error'):
        status_code = 404 if 'NOT_FOUND' in result['error'] else 400
        return jsonify({
            "status": "error",
            "error_code": result['error'],
            "message": result['message']
        }), status_code
    
    return jsonify(result), 200

@employees_bp.route('/api/v1/partner-employees', methods=['POST'])
@require_auth
def create_employee():
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "error_code": "INVALID_REQUEST",
            "message": "Dữ liệu không hợp lệ"
        }), 400
    
    full_name = data.get('full_name')
    email = data.get('email')
    role_id = data.get('role_id')
    
    if not full_name or not email or not role_id:
        return jsonify({
            "status": "error",
            "error_code": "MISSING_FIELDS",
            "message": "Thiếu thông tin bắt buộc"
        }), 400
    
    result = employee_service.create_employee(full_name, email, str(role_id))
    
    if result.get('error'):
        status_code = 409 if result['error'] == 'EMAIL_ALREADY_EXISTS' else 400
        return jsonify({
            "status": "error",
            "error_code": result['error'],
            "message": result['message']
        }), status_code
    
    return jsonify(result), 201

@employees_bp.route('/api/v1/partner-employees/<employee_id>', methods=['PUT'])
@require_auth
def update_employee(employee_id):
    """Update employee - full_name, email, password, role_id, status as per H27"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "error_code": "INVALID_REQUEST",
            "message": "Dữ liệu không hợp lệ"
        }), 400
    
    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    role_id = data.get('role_id')
    status = data.get('status')
    
    result = employee_service.update_employee(
        employee_id,
        full_name=full_name,
        email=email,
        password=password,
        role_id=str(role_id) if role_id else None,
        status=status
    )
    
    if result.get('error'):
        status_code = 404 if 'NOT_FOUND' in result['error'] else 400
        if result['error'] == 'EMAIL_ALREADY_EXISTS':
            status_code = 409
        return jsonify({
            "status": "error",
            "error_code": result['error'],
            "message": result['message']
        }), status_code
    
    return jsonify(result), 200

@employees_bp.route('/api/v1/partner-employees/<employee_id>', methods=['DELETE'])
@require_auth
def delete_employee(employee_id):
    lock_only = request.args.get('lock_only', 'false').lower() == 'true'
    
    result = employee_service.delete_employee(employee_id, lock_only=lock_only)
    
    if result.get('error'):
        status_code = 404 if 'NOT_FOUND' in result['error'] else 400
        return jsonify({
            "status": "error",
            "error_code": result['error'],
            "message": result['message']
        }), status_code
    
    return jsonify(result), 200

@jwks_bp.route('/.well-known/jwks.json', methods=['GET'])
def get_jwks():
    keys = jwt_service.get_all_active_keys()
    
    jwks_keys = []
    for key in keys:
        jwks_keys.append({
            "kid": key["kid"],
            "kty": "RSA",
            "alg": key["algorithm"],
            "public_key": key["public_key"],
            "use": key["use"]
        })
    
    return jsonify(jwks_keys), 200
