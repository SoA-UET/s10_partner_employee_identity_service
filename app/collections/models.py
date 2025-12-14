from typing import TypedDict
from bson import ObjectId

class Role(TypedDict):
    _id: ObjectId
    name: str
    permissions: list[str]

class Employee(TypedDict):
    _id: ObjectId
    role_id: ObjectId
    email: str
    password_hash: str
    full_name: str
    status: str
    failed_login_attempts: int
    locked_until: str | None

class SigningKey(TypedDict):
    _id: ObjectId
    kid: str
    private_key: str
    public_key: str
    algorithm: str
    use: str
    created_at: str
    is_active: bool
