# API Documentation - Partner Employee Identity Service (S10)

## Base URL
```
http://localhost:7010
```

## Authentication
Hầu hết các endpoints yêu cầu JWT token trong header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. Health Check

```http
GET /
```

**Response:**
```json
{
  "service": "Partner Employee Identity Service (S10)",
  "version": "0.1.0",
  "status": "running"
}
```

---

### 2. Login

```http
POST /api/v1/partner-auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "admin@partner.vn",
  "password": "Admin@123"
}
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Đăng nhập đối tác thành công",
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjEyMzQ1Njc4LTkwYWItY2RlZi0xMjM0LTU2Nzg5MGFiY2RlZiJ9...",
  "token_type": "Bearer",
  "expires_in": 600,
  "partner_employee": {
    "employee_id": "507f1f77bcf86cd799439011",
    "full_name": "Nguyen Van Admin",
    "role": "PARTNER_ADMIN",
    "status": "ACTIVE"
  }
}
```

**Error Responses:**

401 Unauthorized - Sai thông tin đăng nhập:
```json
{
  "status": "error",
  "error_code": "INVALID_CREDENTIALS",
  "message": "Sai tên đăng nhập hoặc mật khẩu"
}
```

403 Forbidden - Tài khoản bị khóa:
```json
{
  "status": "error",
  "error_code": "ACCOUNT_LOCKED",
  "message": "Tài khoản bị khóa do đăng nhập sai nhiều lần"
}
```

---

### 3. Get JWKS (Public Keys)

```http
GET /.well-known/jwks.json
```

**Response (200 OK):**
```json
{
  "keys": [
    {
      "kid": "12345678-90ab-cdef-1234-567890abcdef",
      "kty": "RSA",
      "alg": "RS256",
      "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkq...\n-----END PUBLIC KEY-----",
      "use": "sig"
    }
  ]
}
```

---

### 4. Create Employee

```http
POST /api/v1/partner-employees
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "full_name": "Tran Van C",
  "email": "employee@partner.vn",
  "role_id": "507f1f77bcf86cd799439011"
}
```

**Success Response (201 Created):**
```json
{
  "status": "success",
  "employee_id": "507f191e810c19729de860ea",
  "message": "Tạo tài khoản nhân viên đối tác thành công và đã gửi email kích hoạt",
  "default_password": "Abc123!@#Xyz"
}
```

**Error Responses:**

409 Conflict - Email đã tồn tại:
```json
{
  "status": "error",
  "error_code": "EMAIL_ALREADY_EXISTS",
  "message": "Email đã tồn tại"
}
```

---

### 5. Update Employee

```http
PUT /api/v1/partner-employees/{employee_id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "full_name": "Tran Van C Updated",
  "role_id": "507f1f77bcf86cd799439012",
  "status": "ACTIVE"
}
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Cập nhật tài khoản nhân viên đối tác thành công"
}
```

---

### 6. Delete/Disable Employee

```http
DELETE /api/v1/partner-employees/{employee_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `lock_only` (optional): `true` để chỉ khóa tạm thời, `false` hoặc không có để vô hiệu hóa

**Examples:**
```http
DELETE /api/v1/partner-employees/507f191e810c19729de860ea
DELETE /api/v1/partner-employees/507f191e810c19729de860ea?lock_only=true
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Tài khoản nhân viên đối tác đã bị vô hiệu hóa"
}
```

---

## Security Features

### Rate Limiting
- Tối đa 5 lần đăng nhập sai
- Tài khoản sẽ bị khóa 30 phút sau 5 lần sai

### JWT Token
- Algorithm: RS256
- Expiration: 10 phút (configurable)
- Header bao gồm `kid` để tham chiếu signing key

### Password Security
- Sử dụng bcrypt để hash passwords
- Default password được tạo ngẫu nhiên có độ dài 12 ký tự

---

## Testing với cURL

### Login
```bash
curl -X POST http://localhost:7010/api/v1/partner-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@partner.vn","password":"Admin@123"}'
```

### Get JWKS
```bash
curl http://localhost:7010/.well-known/jwks.json
```

### Create Employee (Windows)
```bash
set TOKEN=your_token_here
curl -X POST http://localhost:7010/api/v1/partner-employees ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -d "{\"full_name\":\"Test User\",\"email\":\"test@partner.vn\",\"role_id\":\"507f1f77bcf86cd799439011\"}"
```

---

## Error Codes

| Code | Description |
|------|-------------|
| INVALID_CREDENTIALS | Sai username hoặc password |
| ACCOUNT_LOCKED | Tài khoản bị khóa do login sai nhiều lần |
| TOKEN_EXPIRED | JWT token đã hết hạn |
| INVALID_TOKEN | JWT token không hợp lệ |
| EMAIL_ALREADY_EXISTS | Email đã được sử dụng |
| EMPLOYEE_NOT_FOUND | Không tìm thấy employee |
| ROLE_NOT_FOUND | Không tìm thấy role |
| UNAUTHORIZED | Không có quyền truy cập |

---

## Database Collections

### roles
```javascript
{
  _id: ObjectId("..."),
  name: "PARTNER_ADMIN",
  permissions: ["employee.read", "employee.write", "admin.manage"]
}
```

### employees
```javascript
{
  _id: ObjectId("..."),
  role_id: ObjectId("..."),
  email: "admin@partner.vn",
  password_hash: "$2b$12$...",
  full_name: "Nguyen Van Admin",
  status: "ACTIVE",
  failed_login_attempts: 0,
  locked_until: null
}
```

### signing_keys
```javascript
{
  _id: ObjectId("..."),
  kid: "12345678-90ab-cdef-1234-567890abcdef",
  private_key: "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
  public_key: "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
  algorithm: "RS256",
  use: "sig",
  created_at: "2025-12-14T10:30:00.000Z",
  is_active: true
}
```
