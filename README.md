# Partner Employee Identity Service (S10)

Service quản lý identity và authentication cho nhân viên Partner trong hệ thống Telcenter.

## Tính năng chính

- Đăng nhập với JWT authentication (RS256)
- Quản lý tài khoản nhân viên (CRUD)
- Quản lý roles và permissions
- JWKS endpoint để expose public keys
- Rate limiting và account locking
- Audit logging

## Yêu cầu hệ thống

- Python 3.12+
- MongoDB
- RabbitMQ (nếu cần)

## Cài đặt

1. Clone repository và di chuyển vào thư mục:
```bash
cd telcenter-base-service
```

2. Cài đặt uv (nếu chưa có):
```bash
pip install uv
```

3. Tạo virtual environment và cài đặt dependencies:
```bash
uv sync
```

4. Tạo file `.env` từ template:
```bash
copy .env.example .env
```

5. Cập nhật cấu hình trong `.env` theo môi trường của bạn

## Khởi chạy service

### Khởi động MongoDB (nếu local)
```bash
mongod --dbpath <your-db-path>
```

### Setup database với dữ liệu mẫu
```bash
uv run python setup_db.py
```

### Chạy service
```bash
uv run python -m app
```

Service sẽ chạy tại `http://localhost:7010`

## Test Interface

Mở file `test-interface.html` trong trình duyệt để test các API endpoints.

## API Endpoints

### Authentication
- `POST /api/v1/partner-auth/login` - Đăng nhập

### Employee Management (Cần JWT token)
- `POST /api/v1/partner-employees` - Tạo nhân viên mới
- `PUT /api/v1/partner-employees/{employee_id}` - Cập nhật thông tin nhân viên
- `DELETE /api/v1/partner-employees/{employee_id}` - Xóa/khóa nhân viên

### JWKS
- `GET /.well-known/jwks.json` - Lấy public keys

## Database Schema

### Collection: `roles`
```json
{
  "_id": ObjectId,
  "name": "string (unique)",
  "permissions": ["array", "of", "strings"]
}
```

### Collection: `employees`
```json
{
  "_id": ObjectId,
  "role_id": ObjectId,
  "email": "string (unique)",
  "password_hash": "string",
  "full_name": "string",
  "status": "ACTIVE|INACTIVE|LOCKED",
  "failed_login_attempts": 0,
  "locked_until": "ISO datetime or null"
}
```

### Collection: `signing_keys`
```json
{
  "_id": ObjectId,
  "kid": "UUID string",
  "private_key": "PEM string",
  "public_key": "PEM string",
  "algorithm": "RS256",
  "use": "sig",
  "created_at": "ISO datetime",
  "is_active": true
}
```

## Dữ liệu mẫu

Sau khi chạy `setup_db.py`, bạn có thể đăng nhập với:

**Admin Account:**
- Username: `admin@partner.vn`
- Password: `Admin@123`

**Staff Account:**
- Username: `staff@partner.vn`
- Password: `Staff@123`

## Security Features

- JWT signing với RS256 algorithm
- Password hashing với bcrypt
- Account locking sau 5 lần đăng nhập sai
- JWT token expiration (configurable)
- Audit logging cho tất cả actions

## Troubleshooting

### MongoDB connection error
Đảm bảo MongoDB đang chạy và `MONGO_URL` trong `.env` đúng.

### Port already in use
Thay đổi `FLASK_PORT` trong `.env` thành port khác.

### JWT verification failed
Kiểm tra xem signing key đã được tạo chưa bằng cách gọi `/health` endpoint.
