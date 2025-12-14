import bcrypt
from pymongo.collection import Collection
from datetime import datetime, timedelta
from .JWTService import JWTService
import os

class AuthService:
    def __init__(self, employees_collection: Collection, roles_collection: Collection, 
                 jwt_service: JWTService, logger):
        self.employees_collection = employees_collection
        self.roles_collection = roles_collection
        self.jwt_service = jwt_service
        self.logger = logger
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lock_duration_minutes = int(os.getenv("LOGIN_LOCK_DURATION_MINUTES", "30"))
    
    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def login(self, username: str, password: str):
        employee = self.employees_collection.find_one({"email": username})
        
        if not employee:
            self.logger.log("WARN", f"Login attempt with non-existent username: {username}", action="LOGIN_FAILED")
            return {"error": "INVALID_CREDENTIALS", "message": "Sai tên đăng nhập hoặc mật khẩu"}
        
        if employee.get("locked_until"):
            locked_until = datetime.fromisoformat(employee["locked_until"])
            if datetime.now() < locked_until:
                self.logger.log("WARN", f"Login attempt on locked account: {username}", 
                              user_id=str(employee["_id"]), action="LOGIN_LOCKED")
                return {"error": "ACCOUNT_LOCKED", "message": "Tài khoản bị khóa do đăng nhập sai nhiều lần"}
            else:
                self.employees_collection.update_one(
                    {"_id": employee["_id"]},
                    {"$set": {"locked_until": None, "failed_login_attempts": 0}}
                )
                employee["locked_until"] = None
                employee["failed_login_attempts"] = 0
        
        if not self.verify_password(password, employee["password_hash"]):
            failed_attempts = employee.get("failed_login_attempts", 0) + 1
            update_data = {"failed_login_attempts": failed_attempts}
            
            if failed_attempts >= self.max_login_attempts:
                locked_until = datetime.now() + timedelta(minutes=self.lock_duration_minutes)
                update_data["locked_until"] = locked_until.isoformat()
                self.logger.log("WARN", f"Account locked due to too many failed attempts: {username}",
                              user_id=str(employee["_id"]), action="ACCOUNT_LOCKED")
            
            self.employees_collection.update_one(
                {"_id": employee["_id"]},
                {"$set": update_data}
            )
            
            self.logger.log("WARN", f"Invalid password for user: {username}", 
                          user_id=str(employee["_id"]), action="LOGIN_FAILED")
            
            if failed_attempts >= self.max_login_attempts:
                return {"error": "ACCOUNT_LOCKED", "message": "Tài khoản bị khóa do đăng nhập sai nhiều lần"}
            
            return {"error": "INVALID_CREDENTIALS", "message": "Sai tên đăng nhập hoặc mật khẩu"}
        
        self.employees_collection.update_one(
            {"_id": employee["_id"]},
            {"$set": {"failed_login_attempts": 0, "locked_until": None}}
        )
        
        role = self.roles_collection.find_one({"_id": employee["role_id"]})
        
        if not role:
            self.logger.log("ERROR", f"Role not found for employee: {username}",
                          user_id=str(employee["_id"]), action="LOGIN_ERROR")
            return {"error": "INTERNAL_ERROR", "message": "Lỗi hệ thống"}
        
        token_payload = {
            "sub": str(employee["_id"]),
            "full_name": employee["full_name"],
            "email": employee["email"],
            "permissions": role.get("permissions", [])
        }
        
        access_token = self.jwt_service.sign_token(token_payload)
        
        self.logger.log("INFO", f"Successful login: {username}",
                      user_id=str(employee["_id"]), action="LOGIN_SUCCESS")
        
        return {
            "status": "success",
            "message": "Đăng nhập đối tác thành công",
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.jwt_service.expiration_minutes * 60,
            "partner_employee": {
                "employee_id": str(employee["_id"]),
                "full_name": employee["full_name"],
                "role": role["name"],
                "status": employee.get("status", "ACTIVE")
            }
        }
