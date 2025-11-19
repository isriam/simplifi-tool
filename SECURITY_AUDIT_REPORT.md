# Security Audit Report
**Date:** 2025-11-19
**Application:** Quicken Simplifi Transaction Downloader
**Auditor:** Claude Security Review
**Severity Levels:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low | ✅ Good Practice

---

## Executive Summary

This security audit identified **8 security vulnerabilities** and **4 compliance concerns** in the Quicken Simplifi Transaction Downloader application. The most critical issues involve Cross-Site Scripting (XSS), missing CSRF protection, insecure session management, and inadequate input validation.

**Risk Level: HIGH** - Immediate remediation recommended for critical and high-severity issues.

---

## 🔴 CRITICAL VULNERABILITIES

### 1. Cross-Site Scripting (XSS) via innerHTML

**Location:** `webapp.py:327, 376, 399, 442, 487`

**Issue:**
The web application uses `innerHTML` to inject JSON data directly into the DOM without sanitization. This creates a **stored XSS vulnerability** where malicious transaction data from Quicken Simplifi could execute arbitrary JavaScript.

```javascript
// Vulnerable code:
resultsDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
```

**Attack Scenario:**
1. Attacker creates a transaction with malicious merchant name: `<img src=x onerror=alert('XSS')>`
2. User downloads transactions via web interface
3. Malicious script executes in user's browser
4. Attacker could steal session data, credentials, or financial information

**Remediation:**
```javascript
// Safe approach:
resultsDiv.textContent = JSON.stringify(data, null, 2);
// OR use a pre element's textContent:
const pre = document.createElement('pre');
pre.textContent = JSON.stringify(data, null, 2);
resultsDiv.innerHTML = '';
resultsDiv.appendChild(pre);
```

**Financial Compliance Impact:**
⚠️ PCI DSS Requirement 6.5.7 - Violation (XSS prevention)

---

### 2. No CSRF Protection

**Location:** `webapp.py` - All POST endpoints

**Issue:**
The FastAPI application has **no CSRF token validation** on state-changing operations. All endpoints (`/api/login`, `/api/transactions`, `/api/logout`) are vulnerable to Cross-Site Request Forgery attacks.

**Attack Scenario:**
1. User logs into the application
2. Attacker tricks user into visiting malicious site
3. Malicious site sends POST request to `/api/transactions` or `/api/logout`
4. Application processes request using user's session
5. Attacker downloads user's financial data or disrupts their session

**Affected Endpoints:**
- `POST /api/login` (line 549)
- `POST /api/transactions` (line 604)
- `POST /api/summary` (line 663)
- `POST /api/logout` (line 708)

**Remediation:**
```python
from fastapi_csrf_protect import CsrfProtect

# Add CSRF protection middleware
@app.post("/api/transactions")
async def download_transactions(request: TransactionRequest, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    # ... rest of code
```

**Financial Compliance Impact:**
⚠️ OWASP Top 10:2021 A01 - Broken Access Control

---

## 🟠 HIGH SEVERITY VULNERABILITIES

### 3. Insecure Session Management

**Location:** `webapp.py:26`

**Issue:**
The application uses a **global variable** (`client_instance`) to store authenticated sessions. This creates multiple security issues:

```python
# Line 26 - Vulnerable code:
client_instance = None
```

**Problems:**
1. **Session Sharing**: All users share the same global session - if User A logs in, User B can access User A's data
2. **No Session Timeout**: Sessions persist indefinitely with no expiration
3. **No Session Invalidation**: Closing browser doesn't terminate session
4. **Race Conditions**: Concurrent requests could corrupt session state
5. **Memory Leaks**: Browser instances never cleaned up automatically

**Attack Scenario:**
1. User A logs in at 9:00 AM
2. User B accesses the same server at 9:05 AM (same IP/network)
3. User B can access User A's financial transactions without authentication
4. User A's credentials and financial data exposed

**Remediation:**
```python
from starlette.middleware.sessions import SessionMiddleware
import secrets

# Use proper session management:
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

# Store per-user sessions in a secure store
user_sessions = {}  # Or use Redis for production

@app.post("/api/login")
async def login(request: LoginRequest, session: dict = Depends(get_session)):
    session_id = secrets.token_urlsafe(32)
    user_sessions[session_id] = SimplifiClient(...)
    session['session_id'] = session_id
    # Set expiration time
```

**Financial Compliance Impact:**
⚠️ PCI DSS Requirement 8.2 - User authentication must be unique per user
⚠️ SOC 2 - Access control violations

---

### 4. Missing Authentication Checks

**Location:** `webapp.py:574-601`

**Issue:**
While most endpoints check `if not client_instance`, this check is **insufficient** for multi-user scenarios due to the global session issue. Additionally, there's no rate limiting on authentication attempts.

**Problems:**
1. No protection against brute force attacks on `/api/login`
2. Failed login attempts not logged or monitored
3. No account lockout after multiple failed attempts
4. No IP-based rate limiting

**Remediation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(request: LoginRequest):
    # ... implementation
```

**Financial Compliance Impact:**
⚠️ PCI DSS Requirement 8.1.6 - Limit repeated access attempts

---

### 5. Credentials Exposed in Client-Side JavaScript

**Location:** `webapp.py:528-531`

**Issue:**
The application embeds the user's email address directly into JavaScript code:

```javascript
// Line 528-531 - Vulnerable code:
const envEmail = '""" + os.getenv('SIMPLIFI_EMAIL', '') + """';
if (envEmail) {
    document.getElementById('email').value = envEmail;
}
```

**Problems:**
1. Email address exposed in HTML source code to anyone viewing the page
2. If `.env` contains the email, it's visible to all users (not just authenticated)
3. Email could be scraped by bots or malicious actors
4. Potential for credential stuffing attacks

**Remediation:**
```python
# Don't expose credentials in frontend - use backend API:
@app.get("/api/user-email")
async def get_user_email(session: dict = Depends(get_session)):
    if is_authenticated(session):
        return {"email": session.get("email", "")}
    return {"email": ""}
```

**Financial Compliance Impact:**
⚠️ GDPR Article 32 - Security of processing (PII exposure)

---

## 🟡 MEDIUM SEVERITY VULNERABILITIES

### 6. Insufficient Input Validation

**Location:** `webapp.py:29-45, transaction_downloader.py:68-115`

**Issue:**
Input validation is minimal or non-existent for user-supplied data:

**Missing Validations:**
1. **Email format validation** (line 30) - No regex check for valid email
2. **Date format validation** (lines 36-37) - No validation of YYYY-MM-DD format
3. **Amount validation** (lines 40-41) - No check for reasonable ranges (could be negative, extremely large)
4. **String length limits** - No maximum length for merchant, description, category (DoS risk)
5. **Account ID format** - No validation of expected format

**Attack Scenarios:**
- **DoS via long strings**: Send 10MB merchant name to exhaust memory
- **Logic bugs**: Negative amounts could break financial calculations
- **Injection**: Special characters in filters could cause parsing errors

**Remediation:**
```python
from pydantic import BaseModel, validator, EmailStr
from typing import Optional

class TransactionRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    last_days: Optional[int] = 30
    account_id: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    category: Optional[str] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    format: str = "json"

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v

    @validator('last_days')
    def validate_last_days(cls, v):
        if v is not None and (v < 1 or v > 3650):
            raise ValueError('last_days must be between 1 and 3650')
        return v

    @validator('min_amount', 'max_amount')
    def validate_amount(cls, v):
        if v is not None and abs(v) > 1_000_000_000:
            raise ValueError('Amount too large')
        return v

    @validator('category', 'merchant', 'description', 'account_id')
    def validate_string_length(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('Input too long')
        return v

class LoginRequest(BaseModel):
    email: EmailStr  # Pydantic validates email format
    password: str
    headless: bool = True

    @validator('password')
    def validate_password(cls, v):
        if len(v) > 500:
            raise ValueError('Password too long')
        return v
```

---

### 7. Missing Security Headers

**Location:** `webapp.py:728`

**Issue:**
The application doesn't set critical security headers, leaving it vulnerable to various attacks.

**Missing Headers:**
1. `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
2. `X-Frame-Options: DENY` - Prevents clickjacking
3. `Content-Security-Policy` - Prevents XSS and data injection
4. `Strict-Transport-Security` - Enforces HTTPS
5. `X-XSS-Protection: 1; mode=block` - Browser XSS filter

**Remediation:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

### 8. Insecure Browser Automation Configuration

**Location:** `simplifi_client.py:56-59`

**Issue:**
The Playwright browser configuration doesn't implement security best practices:

```python
self.context = self.browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
)
```

**Problems:**
1. No isolation between browser sessions
2. User agent spoofing could violate Quicken's ToS
3. No timeout settings for network requests (potential DoS)
4. Screenshots could be saved containing sensitive financial data
5. No protection against browser fingerprinting

**Remediation:**
```python
self.context = self.browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    # Don't spoof user agent - be transparent
    ignore_https_errors=False,  # Enforce SSL validation
    java_script_enabled=True,
    accept_downloads=False,  # Prevent unexpected file downloads
    service_workers='block',  # Reduce tracking
    bypass_csp=False,  # Respect CSP
    locale='en-US',
    timezone_id='America/New_York',
    record_video_dir=None,  # Don't record sensitive sessions
)
```

---

## 🟢 LOW SEVERITY ISSUES

### 9. Verbose Error Messages

**Location:** Multiple locations (e.g., `webapp.py:571, 586, 601`)

**Issue:**
Error messages expose internal implementation details:

```python
raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")
```

**Problem:**
Detailed error messages could reveal:
- File paths
- Database schema
- Library versions
- Internal logic

**Remediation:**
```python
# Log detailed errors server-side
logger.error(f"Login error: {str(e)}", exc_info=True)
# Return generic message to client
raise HTTPException(status_code=500, detail="An error occurred during login")
```

---

### 10. No HTTPS Enforcement

**Location:** `webapp.py:728`

**Issue:**
Application runs on HTTP (port 8000) with no HTTPS enforcement.

**Problem:**
- Credentials transmitted in plaintext over network
- Session cookies vulnerable to interception
- Financial data exposed to network sniffing

**Remediation:**
```python
import ssl

if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain('cert.pem', 'key.pem')

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
```

---

## 💰 FINANCIAL COMPLIANCE CONCERNS

### 1. PCI DSS Compliance Issues

**Relevant Requirements Violated:**

| Requirement | Issue | Status |
|-------------|-------|--------|
| 6.5.7 - XSS Prevention | innerHTML vulnerability | ❌ Non-compliant |
| 8.1.6 - Limit access attempts | No rate limiting | ❌ Non-compliant |
| 8.2 - Unique user IDs | Global session sharing | ❌ Non-compliant |
| 8.2.3 - Strong authentication | No 2FA enforcement | ⚠️ Partial |
| 10.2 - Audit logging | No activity logs | ❌ Non-compliant |

**Note:** While this application doesn't process credit card data directly, it accesses financial accounts and should follow PCI DSS principles.

---

### 2. GDPR/Privacy Concerns

**Issues:**
1. **No privacy policy or consent mechanism**
2. **Email exposed in client-side code** (Article 32 - Security of processing)
3. **No data retention policy** - CSV/JSON exports saved indefinitely
4. **No encryption at rest** for exported financial data
5. **No right to erasure mechanism**

**Recommendations:**
- Implement data encryption for exported files
- Add file auto-deletion after download
- Create privacy policy
- Add consent checkboxes for data processing
- Implement audit logging for GDPR compliance

---

### 3. SOC 2 Concerns

**Issues:**
1. **Access Control** - Global session allows unauthorized access
2. **Change Management** - No versioning or audit trail for configuration
3. **Logical Access** - No user role management
4. **System Monitoring** - No logging or alerting

---

### 4. Data Exposure Risks

**Sensitive Data at Risk:**
1. Bank account numbers
2. Transaction descriptions (potentially revealing personal info)
3. Merchant names (location tracking)
4. Financial patterns (spending habits)
5. Account balances

**Current Protection:** None - all data stored in plaintext CSV/JSON

**Recommendation:**
```python
# Encrypt exported files
from cryptography.fernet import Fernet

def export_to_csv_encrypted(transactions, filename, encryption_key):
    # Export to CSV
    csv_data = df.to_csv(index=False)

    # Encrypt
    f = Fernet(encryption_key)
    encrypted = f.encrypt(csv_data.encode())

    # Save encrypted file
    with open(f"{filename}.encrypted", 'wb') as file:
        file.write(encrypted)
```

---

## ✅ GOOD SECURITY PRACTICES FOUND

1. ✅ **Credentials in .env** - Not hardcoded (simplifi_client.py:32-33)
2. ✅ **.env in .gitignore** - Properly excluded from version control
3. ✅ **Context managers** - Proper resource cleanup (simplifi_client.py:42-49)
4. ✅ **HTTPS to Simplifi** - All external requests use HTTPS
5. ✅ **No SQL database** - No SQL injection risk (uses browser scraping)
6. ✅ **Minimal dependencies** - Reduces supply chain risk
7. ✅ **No eval() usage** - No arbitrary code execution
8. ✅ **Type hints** - Good code quality and type safety

---

## 📊 RISK SUMMARY

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 Critical | 2 | XSS vulnerability, No CSRF protection |
| 🟠 High | 3 | Session management, Auth checks, Credential exposure |
| 🟡 Medium | 3 | Input validation, Security headers, Browser config |
| 🟢 Low | 2 | Error messages, No HTTPS |
| **Total** | **10** | |

---

## 🎯 PRIORITIZED REMEDIATION PLAN

### Immediate (Within 24 hours)
1. ✅ **Fix XSS vulnerability** - Replace `innerHTML` with `textContent`
2. ✅ **Implement session management** - Use proper session middleware
3. ✅ **Add CSRF protection** - Install and configure CSRF tokens

### Short-term (Within 1 week)
4. Add input validation with Pydantic validators
5. Implement rate limiting on login endpoint
6. Add security headers middleware
7. Enable HTTPS with SSL certificates
8. Remove credential exposure from JavaScript

### Medium-term (Within 1 month)
9. Add comprehensive audit logging
10. Implement file encryption for exports
11. Add data retention policies
12. Create privacy policy and consent mechanism
13. Add automated security testing (SAST/DAST)

### Long-term (Within 3 months)
14. Implement proper user management system
15. Add role-based access control (RBAC)
16. Set up security monitoring and alerting
17. Conduct penetration testing
18. Implement SOC 2 controls

---

## 🔧 DEPENDENCY SECURITY

**Current Dependencies:**
```
playwright>=1.40.0          ✅ Latest (1.49.0 available)
python-dotenv>=1.0.0        ✅ Latest
pandas>=2.0.0               ✅ Latest (2.2.3 available)
beautifulsoup4>=4.12.0      ✅ Latest
fastapi>=0.104.0            ⚠️ Outdated (0.115.5 available)
uvicorn[standard]>=0.24.0   ⚠️ Outdated (0.34.0 available)
```

**Recommendations:**
```bash
# Update dependencies:
pip install --upgrade fastapi uvicorn

# Add security dependencies:
pip install fastapi-csrf-protect slowapi cryptography
```

---

## 📝 ADDITIONAL RECOMMENDATIONS

### 1. Security Testing
```bash
# Install security scanners:
pip install bandit safety

# Run security checks:
bandit -r . -ll
safety check
```

### 2. Code Quality
```bash
# Add pre-commit hooks:
pip install pre-commit
# Create .pre-commit-config.yaml with security checks
```

### 3. Documentation
- Create SECURITY.md with vulnerability reporting process
- Document security architecture
- Create incident response plan

### 4. Monitoring
```python
# Add logging:
import logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log security events:
logging.warning(f"Failed login attempt from {request.client.host}")
```

---

## 🎓 DEVELOPER SECURITY TRAINING

**Recommended Topics:**
1. OWASP Top 10 (2021)
2. Secure coding in Python
3. Web application security
4. API security best practices
5. Financial data protection

---

## 📚 REFERENCES

1. [OWASP Top 10](https://owasp.org/www-project-top-ten/)
2. [PCI DSS Requirements](https://www.pcisecuritystandards.org/)
3. [GDPR Guidelines](https://gdpr.eu/)
4. [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
5. [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)

---

## ✍️ SIGN-OFF

**Audit Completed:** 2025-11-19
**Status:** Ready for remediation
**Next Review:** After critical fixes implemented

**Contact:** For questions about this audit, please open a GitHub issue.

---

**DISCLAIMER:** This audit was performed based on static code analysis. A full penetration test is recommended before production deployment.
