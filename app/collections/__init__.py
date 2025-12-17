from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
import os
from dotenv import load_dotenv

load_dotenv()

class Collections:
    def __init__(self):
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/partner_identity_db")
        self.client = MongoClient(mongo_url)
        db_name = mongo_url.split("/")[-1]
        self.db: Database = self.client[db_name]
        
        self.roles = self.db["roles"]
        self.employees = self.db["employees"]
        self.signing_keys = self.db["signing_keys"]
        
        self._setup_indexes()
    def _setup_indexes(self):
        self.roles.create_index([("name", ASCENDING)], unique=True)
        self.employees.create_index([("email", ASCENDING)], unique=True)
        self.signing_keys.create_index([("kid", ASCENDING)], unique=True)
        self.signing_keys.create_index([("is_active", ASCENDING)])
