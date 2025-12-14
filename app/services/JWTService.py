import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
from pymongo.collection import Collection
import uuid
import os

class JWTService:
    def __init__(self, signing_keys_collection: Collection, logger):
        self.signing_keys_collection = signing_keys_collection
        self.logger = logger
        self.expiration_minutes = int(os.getenv("JWT_EXPIRATION_TIME_IN_MINUTES", "10"))
    
    def generate_key_pair(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode('utf-8'), public_pem.decode('utf-8')
    
    def create_signing_key(self):
        kid = str(uuid.uuid4())
        private_key, public_key = self.generate_key_pair()
        
        key_doc = {
            "kid": kid,
            "private_key": private_key,
            "public_key": public_key,
            "algorithm": "RS256",
            "use": "sig",
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        self.signing_keys_collection.insert_one(key_doc)
        self.logger.log("INFO", f"Created new signing key with kid: {kid}")
        return key_doc
    
    def get_latest_active_key(self):
        key = self.signing_keys_collection.find_one(
            {"is_active": True},
            sort=[("created_at", -1)]
        )
        
        if not key:
            self.logger.log("WARN", "No active signing key found, creating new one")
            key = self.create_signing_key()
        
        return key
    
    def get_all_active_keys(self):
        keys = list(self.signing_keys_collection.find(
            {"is_active": True},
            {"_id": 0, "kid": 1, "public_key": 1, "algorithm": 1, "use": 1}
        ))
        return keys
    
    def sign_token(self, payload: dict):
        key = self.get_latest_active_key()
        
        now = datetime.now()
        # Convert to UTC timestamp to avoid timezone issues
        import time
        iat_timestamp = int(time.time())
        exp_timestamp = iat_timestamp + (self.expiration_minutes * 60)
        
        token_payload = {
            **payload,
            "iat": iat_timestamp,
            "exp": exp_timestamp
        }
        
        token = jwt.encode(
            token_payload,
            key["private_key"],
            algorithm="RS256",
            headers={"kid": key["kid"]}
        )
        
        self.logger.log("INFO", f"Signed JWT for user: {payload.get('sub', 'unknown')}")
        return token
    
    def verify_token(self, token: str):
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise ValueError("Token missing kid in header")
            
            key = self.signing_keys_collection.find_one({"kid": kid, "is_active": True})
            
            if not key:
                raise ValueError(f"No active key found for kid: {kid}")
            
            payload = jwt.decode(
                token,
                key["public_key"],
                algorithms=["RS256"]
            )
            
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.log("WARN", "Token expired")
            raise
        except jwt.InvalidTokenError as e:
            self.logger.log("ERROR", f"Invalid token: {str(e)}")
            raise
