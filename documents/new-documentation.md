## 📘 API Documentation (Flask HTTP Endpoints)

---

### **POST /register**

Registers a new user.

**Request JSON:**

```json
{
  "username": "johndoe",
  "email": "johndoe@example.com",
  "password": "securepassword123"
}
```

**Success Response:**

```json
{
  "message": "User registered successfully",
  "user_id": "uuid123",
  "email_verification_required": true
}
```

**Error Responses:**

* `400`: Missing fields
* `409`: Username or email already exists
* `500`: Server error

**Notes:**

* Password should be hashed server-side
* Should trigger email verification (if implemented)

---

### **POST /login**

Authenticates a user and returns a token/session.

**Request JSON:**

```json
{
  "email": "johndoe@example.com",
  "password": "securepassword123"
}
```

**Success Response:**

```json
{
  "message": "Login successful",
  "token": "jwt_or_session_token_here"
}
```

**Error Responses:**

* `401`: Invalid email or password
* `403`: Email not verified (if applicable)

**Notes:**

* Use JWT or session-based tokens for client reuse
* Token should be sent with all future requests or WS handshake

---

### **POST /forgot-password**

Sends a password reset email to the user.

**Request JSON:**

```json
{
  "email": "johndoe@example.com"
}
```

**Success Response:**

```json
{
  "message": "Password reset email sent (if email exists)"
}
```

**Notes:**

* Should always return success (don’t reveal valid emails)

---

### **POST /reset-password**

Allows resetting the password with a token.

**Request JSON:**

```json
{
  "token": "reset_token_string",
  "new_password": "newSecurePassword"
}
```

**Success Response:**

```json
{
  "message": "Password reset successful"
}
```

**Error Responses:**

* `400`: Invalid/expired token
* `422`: Weak password

---

### **GET /verify-email?token=...**

Verifies a user's email using a token.

**Success Response:**

```json
{
  "message": "Email verified successfully"
}
```

**Error Responses:**

* `400`: Invalid or expired token
* `410`: Email already verified

**Notes:**

* Should mark user's email as verified in DB
* Token should expire after use or after a time window

---

(Additional endpoints like `/profile`, `/chat-list`, etc. can be added later as they are implemented.)
