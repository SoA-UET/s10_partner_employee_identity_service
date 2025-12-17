from pymongo.collection import Collection
from ..utils.db import str_to_objectid
import secrets
import string

class EmployeeService:
    def __init__(self, employees_collection: Collection, roles_collection: Collection, 
                 auth_service, logger):
        self.employees_collection = employees_collection
        self.roles_collection = roles_collection
        self.auth_service = auth_service
        self.logger = logger
    
    def generate_default_password(self, length=12):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_employee(self, full_name: str, email: str, role_id: str):
        existing = self.employees_collection.find_one({"email": email})
        if existing:
            return {"error": "EMAIL_ALREADY_EXISTS", "message": "Email đã tồn tại"}
        
        role_object_id = str_to_objectid(role_id)
        if not role_object_id:
            return {"error": "INVALID_ROLE_ID", "message": "Role ID không hợp lệ"}
        
        role = self.roles_collection.find_one({"_id": role_object_id})
        if not role:
            return {"error": "ROLE_NOT_FOUND", "message": "Không tìm thấy vai trò"}
        
        # default_password = self.generate_default_password()
        default_password = "Staff@123"
        password_hash = self.auth_service.hash_password(default_password)
        
        employee_doc = {
            "full_name": full_name,
            "email": email,
            "role_id": role_object_id,
            "password_hash": password_hash,
            "status": "INACTIVE",
            "failed_login_attempts": 0,
            "locked_until": None
        }
        
        result = self.employees_collection.insert_one(employee_doc)
        
        self.logger.log("INFO", f"Created new employee: {email}, default password: {default_password}",
                      user_id=str(result.inserted_id), action="EMPLOYEE_CREATED")
        
        return {
            "status": "success",
            "employee_id": str(result.inserted_id),
            "message": "Tạo tài khoản nhân viên đối tác thành công và đã gửi email kích hoạt",
            "default_password": default_password
        }
    
    def update_employee(self, employee_id: str, full_name: str = None, 
                       email: str = None, password: str = None,
                       role_id: str = None, status: str = None):
        """Update employee - full_name, email, password, role_id, status as per H27"""
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return {"error": "INVALID_EMPLOYEE_ID", "message": "Employee ID không hợp lệ"}
        
        employee = self.employees_collection.find_one({"_id": object_id})
        if not employee:
            return {"error": "EMPLOYEE_NOT_FOUND", "message": "Không tìm thấy nhân viên"}
        
        update_data = {}
        
        if full_name:
            update_data["full_name"] = full_name
        
        if email:
            # Check if new email already exists
            existing = self.employees_collection.find_one({"email": email, "_id": {"$ne": object_id}})
            if existing:
                return {"error": "EMAIL_ALREADY_EXISTS", "message": "Email đã được sử dụng"}
            update_data["email"] = email
        
        if password:
            # Hash new password
            password_hash = self.auth_service.hash_password(password)
            update_data["password_hash"] = password_hash
            update_data["failed_login_attempts"] = 0
            update_data["locked_until"] = None
        
        if role_id:
            role_object_id = str_to_objectid(role_id)
            if not role_object_id:
                return {"error": "INVALID_ROLE_ID", "message": "Role ID không hợp lệ"}
            
            role = self.roles_collection.find_one({"_id": role_object_id})
            if not role:
                return {"error": "ROLE_NOT_FOUND", "message": "Không tìm thấy vai trò"}
            
            update_data["role_id"] = role_object_id
        
        if status:
            update_data["status"] = status
        
        if update_data:
            self.employees_collection.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
        
        self.logger.log("INFO", f"Updated employee: {employee_id} - fields: {', '.join(update_data.keys())}",
                      user_id=employee_id, action="EMPLOYEE_UPDATED")
        
        return {
            "status": "success",
            "message": "Cập nhật tài khoản nhân viên đối tác thành công"
        }
    
    def delete_employee(self, employee_id: str, lock_only: bool = False):
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return {"error": "INVALID_EMPLOYEE_ID", "message": "Employee ID không hợp lệ"}
        
        employee = self.employees_collection.find_one({"_id": object_id})
        if not employee:
            return {"error": "EMPLOYEE_NOT_FOUND", "message": "Không tìm thấy nhân viên"}
        
        if lock_only:
            self.employees_collection.update_one(
                {"_id": object_id},
                {"$set": {"status": "LOCKED"}}
            )
            message = "Tài khoản nhân viên đối tác đã bị khóa"
            action = "EMPLOYEE_LOCKED"
        else:
            self.employees_collection.update_one(
                {"_id": object_id},
                {"$set": {"status": "DISABLED"}}
            )
            message = "Tài khoản nhân viên đối tác đã bị vô hiệu hóa"
            action = "EMPLOYEE_DISABLED"
        
        self.logger.log("INFO", f"Disabled/locked employee: {employee_id}",
                      user_id=employee_id, action=action)
        
        return {
            "status": "success",
            "message": message
        }
    
    def get_employee(self, employee_id: str):
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return None
        
        return self.employees_collection.find_one({"_id": object_id})
    
    def get_employee_detail(self, employee_id: str):
        """Get employee detail with roles and permissions"""
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return {"error": "INVALID_EMPLOYEE_ID", "message": "Employee ID không hợp lệ"}
        
        employee = self.employees_collection.find_one(
            {"_id": object_id},
            {"password_hash": 0}  # Exclude password hash
        )
        
        if not employee:
            return {"error": "EMPLOYEE_NOT_FOUND", "message": "Không tìm thấy nhân viên"}
        
        # Get role with permissions
        role = self.roles_collection.find_one({"_id": employee["role_id"]})
        
        if role:
            employee["role"] = {
                "id": str(role["_id"]),
                "name": role["name"],
                "permissions": role.get("permissions", [])
            }
            # Remove role_id to avoid duplication
            del employee["role_id"]
        else:
            employee["role"] = None
        
        # Convert ObjectId to string
        employee["_id"] = str(employee["_id"])
        
        return {
            "status": "success",
            "employee": employee
        }
    
    def get_all_employees(self, page: int = 1, limit: int = 10, status: str = None):
        """Get list of employees with pagination"""
        skip = (page - 1) * limit
        
        query = {}
        if status:
            query["status"] = status
        
        employees = list(self.employees_collection.find(
            query,
            {"password_hash": 0}  # Exclude password hash
        ).skip(skip).limit(limit))
        
        total = self.employees_collection.count_documents(query)
        
        # Add role name to each employee
        for emp in employees:
            role = self.roles_collection.find_one({"_id": emp["role_id"]})
            emp["role_name"] = role["name"] if role else "Unknown"
        
        return {
            "employees": employees,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
    
    def change_password(self, employee_id: str, old_password: str, new_password: str):
        """Change employee password"""
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return {"error": "INVALID_EMPLOYEE_ID", "message": "Employee ID không hợp lệ"}
        
        employee = self.employees_collection.find_one({"_id": object_id})
        if not employee:
            return {"error": "EMPLOYEE_NOT_FOUND", "message": "Không tìm thấy nhân viên"}
        
        # Verify old password
        if not self.auth_service.verify_password(old_password, employee["password_hash"]):
            self.logger.log("WARN", f"Failed password change attempt for employee: {employee_id}",
                          user_id=employee_id, action="PASSWORD_CHANGE_FAILED")
            return {"error": "INVALID_OLD_PASSWORD", "message": "Mật khẩu cũ không đúng"}
        
        # Hash new password
        new_password_hash = self.auth_service.hash_password(new_password)
        
        # Update password
        self.employees_collection.update_one(
            {"_id": object_id},
            {"$set": {
                "password_hash": new_password_hash,
                "failed_login_attempts": 0,
                "locked_until": None
            }}
        )
        
        self.logger.log("INFO", f"Password changed for employee: {employee_id}",
                      user_id=employee_id, action="PASSWORD_CHANGED")
        
        return {
            "status": "success",
            "message": "Đổi mật khẩu thành công"
        }
    
    def reset_password(self, employee_id: str, new_password: str = None):
        """Reset employee password (admin function)"""
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return {"error": "INVALID_EMPLOYEE_ID", "message": "Employee ID không hợp lệ"}
        
        employee = self.employees_collection.find_one({"_id": object_id})
        if not employee:
            return {"error": "EMPLOYEE_NOT_FOUND", "message": "Không tìm thấy nhân viên"}
        
        # Generate new password if not provided
        if not new_password:
            new_password = self.generate_default_password()
        
        new_password_hash = self.auth_service.hash_password(new_password)
        
        # Update password
        self.employees_collection.update_one(
            {"_id": object_id},
            {"$set": {
                "password_hash": new_password_hash,
                "failed_login_attempts": 0,
                "locked_until": None,
                "status": "INACTIVE"  # Require reactivation after reset
            }}
        )
        
        self.logger.log("INFO", f"Password reset for employee: {employee_id}, new password: {new_password}",
                      user_id=employee_id, action="PASSWORD_RESET")
        
        return {
            "status": "success",
            "message": "Reset mật khẩu thành công",
            "new_password": new_password
        }
    
    def update_employee_email(self, employee_id: str, new_email: str):
        """Update employee email"""
        object_id = str_to_objectid(employee_id)
        if not object_id:
            return {"error": "INVALID_EMPLOYEE_ID", "message": "Employee ID không hợp lệ"}
        
        employee = self.employees_collection.find_one({"_id": object_id})
        if not employee:
            return {"error": "EMPLOYEE_NOT_FOUND", "message": "Không tìm thấy nhân viên"}
        
        # Check if new email already exists
        existing = self.employees_collection.find_one({"email": new_email, "_id": {"$ne": object_id}})
        if existing:
            return {"error": "EMAIL_ALREADY_EXISTS", "message": "Email đã được sử dụng"}
        
        self.employees_collection.update_one(
            {"_id": object_id},
            {"$set": {"email": new_email}}
        )
        
        self.logger.log("INFO", f"Email updated for employee: {employee_id} to {new_email}",
                      user_id=employee_id, action="EMAIL_UPDATED")
        
        return {
            "status": "success",
            "message": "Cập nhật email thành công"
        }
