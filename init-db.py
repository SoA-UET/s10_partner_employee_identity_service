"""
Initialize database with default roles and admin account
"""
from dotenv import load_dotenv
load_dotenv()

from app.collections import Collections
from app.services.JWTService import JWTService
from app.services.AuthService import AuthService
from app.services.LoggerService import LoggerService

collections = Collections()
roles_collection = collections.roles
employees_collection = collections.employees
signing_keys_collection = collections.signing_keys

logger_service = LoggerService()

jwt_service = JWTService(
    signing_keys_collection=signing_keys_collection,
    logger=logger_service,
)


auth_service = AuthService(
    employees_collection=employees_collection,
    roles_collection=roles_collection,
    jwt_service=jwt_service,
    logger=logger_service,
)

hash_password = auth_service.hash_password

from datetime import datetime

from bson import ObjectId


def init_database():
    """
    Initialize database with default data
    """
    print("Initializing database...")
    
    # Check if roles already exist
    existing_roles = list(roles_collection.find())
    if existing_roles:
        print(f"Found {len(existing_roles)} existing roles. Skipping role creation.")
    else:
        # Create default roles
        roles = [
            {
                "_id": ObjectId("694025ac0496f58b284da758"),
                "name": "PARTNER_ADMIN",
                "permissions": [
                    "employee.read",
                    "employee.write",
                    "employee.delete",
                    "admin.manage",
                    "consult_audio",
                    "consult_text"
                ]
            },
            {
                "_id": ObjectId("694025ac0496f58b284da759"),
                "name": "Tư vấn viên kênh thoại",
                "permissions": [
                    "consult_audio"
                ]
            },
            {
                "_id": ObjectId("694025ac0496f58b284da75a"),
                "name": "Tư vấn viên kênh nhắn tin",
                "permissions": [
                    "consult_text"
                ]
            }
        ]
        
        inserted_roles = []
        for role in roles:
            result = roles_collection.update_one({ "_id": role["_id"] }, { "$set": role }, upsert=True)
            inserted_roles.append({**role, "_id": result.upserted_id})
            print(f"Created role: {role['name']}")
        
        # Find ADMIN role
        admin_role = next(r for r in inserted_roles if r["name"] == "ADMIN")
        
        # Check if admin account already exists
        existing_admin = employees_collection.find_one({"email": "admin_partner@telcenter.vn"})
        if existing_admin:
            print("Admin account already exists. Skipping admin creation.")
        else:
            # Create admin account
            admin_password = "Admin@123"
            admin_doc = {
                "full_name": "Admin Partner",
                "email": "admin_partner@telcenter.vn",
                "password_hash": hash_password(admin_password),
                "role_id": admin_role["_id"],
                "status": "ACTIVE",
                "created_at": datetime.now()
            }
            
            employees_collection.insert_one(admin_doc)
            print(f"Created admin account:")
            print(f"  Email: admin_partner@telcenter.vn")
            print(f"  Password: {admin_password}")
    
    print("\nDatabase initialization complete!")
    print("\nYou can now login with:")
    print("  Username: admin_partner@telcenter.vn")
    print("  Password: Admin@123")

if __name__ == "__main__":
    init_database()
