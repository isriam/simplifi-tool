"""
FastAPI Web Application for Quicken Simplifi Transaction Downloader
Provides a web interface to run all Python scripts and functions.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import json
import uvicorn
from dotenv import load_dotenv
import logging
import secrets

from simplifi_client import SimplifiClient
from transaction_downloader import TransactionDownloader
from report_builder import (
    ReportBuilder,
    ReportFilter,
    TimeGrouping
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

app = FastAPI(title="Quicken Simplifi Transaction Downloader", version="1.0.0")

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add session middleware with secure secret key
SESSION_SECRET_KEY = os.getenv('SESSION_SECRET_KEY', secrets.token_urlsafe(32))
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, max_age=3600)

# Session store for client instances (replaces global variable)
# In production, consider using Redis or similar
user_sessions: Dict[str, SimplifiClient] = {}
session_timestamps: Dict[str, datetime] = {}  # Track session creation time
SESSION_TIMEOUT_MINUTES = 60  # Sessions expire after 1 hour


class LoginRequest(BaseModel):
    email: EmailStr  # Validates email format
    password: str = Field(..., min_length=1, max_length=500)
    headless: bool = True

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v):
        if len(v) > 500:
            raise ValueError('Password too long')
        return v


class TransactionRequest(BaseModel):
    start_date: Optional[str] = Field(None, max_length=10)
    end_date: Optional[str] = Field(None, max_length=10)
    last_days: Optional[int] = Field(30, ge=1, le=3650)
    account_id: Optional[str] = Field(None, max_length=500)
    min_amount: Optional[float] = Field(None, ge=-1_000_000_000, le=1_000_000_000)
    max_amount: Optional[float] = Field(None, ge=-1_000_000_000, le=1_000_000_000)
    category: Optional[str] = Field(None, max_length=500)
    merchant: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=500)
    format: str = Field("json", pattern="^(json|csv)$")

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is not None and v != '':
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v

    @field_validator('max_amount')
    @classmethod
    def validate_amount_range(cls, v, info):
        if v is not None and info.data.get('min_amount') is not None:
            if v < info.data['min_amount']:
                raise ValueError('max_amount must be greater than min_amount')
        return v


class ReportRequest(BaseModel):
    """Request model for report generation"""
    report_type: str = Field(..., pattern="^(profit_loss|cash_flow|category_analysis|merchant_analysis|trend_analysis|account_summary)$")
    start_date: Optional[str] = Field(None, max_length=10)
    end_date: Optional[str] = Field(None, max_length=10)
    last_days: Optional[int] = Field(90, ge=1, le=3650)
    min_amount: Optional[float] = Field(None, ge=-1_000_000_000, le=1_000_000_000)
    max_amount: Optional[float] = Field(None, ge=-1_000_000_000, le=1_000_000_000)
    categories: Optional[List[str]] = Field(None, max_length=100)
    exclude_categories: Optional[List[str]] = Field(None, max_length=100)
    merchants: Optional[List[str]] = Field(None, max_length=100)
    exclude_merchants: Optional[List[str]] = Field(None, max_length=100)
    accounts: Optional[List[str]] = Field(None, max_length=100)
    description_contains: Optional[str] = Field(None, max_length=500)
    notes_contains: Optional[str] = Field(None, max_length=500)
    grouping: str = Field("monthly", pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    top_n: Optional[int] = Field(None, ge=1, le=1000)

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is not None and v != '':
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v


class SessionStatus(BaseModel):
    logged_in: bool
    message: str


async def get_client_from_session(request: Request) -> SimplifiClient:
    """Get the client instance from the user's session"""
    session_id = request.session.get('session_id')
    if not session_id or session_id not in user_sessions:
        raise HTTPException(status_code=401, detail="Not logged in. Please login first.")

    # Check if session has expired
    if session_id in session_timestamps:
        session_age = datetime.now() - session_timestamps[session_id]
        if session_age.total_seconds() > (SESSION_TIMEOUT_MINUTES * 60):
            await cleanup_session(session_id)
            request.session.clear()
            raise HTTPException(status_code=401, detail="Session expired. Please login again.")

    return user_sessions[session_id]


async def cleanup_session(session_id: str):
    """Clean up a user session and close the browser"""
    if session_id in user_sessions:
        try:
            await user_sessions[session_id].close()
        except Exception as e:
            logger.error(f"Error closing client for session {session_id}: {e}")
        finally:
            del user_sessions[session_id]

    # Also remove timestamp
    if session_id in session_timestamps:
        del session_timestamps[session_id]


async def cleanup_expired_sessions():
    """Background task to clean up expired sessions"""
    logger.info("Running session cleanup task...")
    expired_sessions = []

    for session_id, timestamp in session_timestamps.items():
        session_age = datetime.now() - timestamp
        if session_age.total_seconds() > (SESSION_TIMEOUT_MINUTES * 60):
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        logger.info(f"Cleaning up expired session: {session_id}")
        await cleanup_session(session_id)

    if expired_sessions:
        logger.info(f"Cleaned up {len(expired_sessions)} expired session(s)")

    return len(expired_sessions)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main web interface"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quicken Simplifi Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .content { padding: 30px; }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #f9f9f9;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        input, select, button {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active { transform: translateY(0); }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        .results {
            margin-top: 20px;
            padding: 15px;
            background: white;
            border-radius: 6px;
            max-height: 400px;
            overflow-y: auto;
        }
        .results pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 12px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 Quicken Simplifi Dashboard</h1>
            <p>Unified web interface for transaction management</p>
        </div>

        <div class="content">
            <div id="statusMessage" class="status"></div>

            <!-- Login Section -->
            <div id="loginSection" class="section">
                <h2>🔐 Login</h2>
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" id="email" placeholder="your.email@example.com">
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" id="password" placeholder="Enter your password">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="headless" checked style="width: auto;">
                        Headless mode (uncheck to see browser for 2FA)
                    </label>
                </div>
                <button onclick="login()">Login to Simplifi</button>
            </div>

            <!-- Main Dashboard (hidden until logged in) -->
            <div id="dashboard" class="hidden">

                <!-- Accounts Section -->
                <div class="section">
                    <h2>📊 Accounts</h2>
                    <button onclick="getAccounts()">List All Accounts</button>
                    <div id="accountsResults" class="results hidden"></div>
                </div>

                <!-- Categories Section -->
                <div class="section">
                    <h2>🏷️ Categories</h2>
                    <button onclick="getCategories()">List All Categories</button>
                    <div id="categoriesResults" class="results hidden"></div>
                </div>

                <!-- Download Transactions Section -->
                <div class="section">
                    <h2>📥 Download Transactions</h2>
                    <div class="grid">
                        <div class="form-group">
                            <label>Last Days:</label>
                            <input type="number" id="lastDays" value="30" min="1">
                        </div>
                        <div class="form-group">
                            <label>Start Date:</label>
                            <input type="date" id="startDate">
                        </div>
                        <div class="form-group">
                            <label>End Date:</label>
                            <input type="date" id="endDate">
                        </div>
                        <div class="form-group">
                            <label>Account ID:</label>
                            <input type="text" id="accountId" placeholder="Optional">
                        </div>
                    </div>
                    <div class="grid">
                        <div class="form-group">
                            <label>Min Amount:</label>
                            <input type="number" id="minAmount" step="0.01" placeholder="Optional">
                        </div>
                        <div class="form-group">
                            <label>Max Amount:</label>
                            <input type="number" id="maxAmount" step="0.01" placeholder="Optional">
                        </div>
                        <div class="form-group">
                            <label>Category:</label>
                            <input type="text" id="category" placeholder="Optional">
                        </div>
                        <div class="form-group">
                            <label>Merchant:</label>
                            <input type="text" id="merchant" placeholder="Optional">
                        </div>
                    </div>
                    <div class="grid">
                        <div class="form-group">
                            <label>Description:</label>
                            <input type="text" id="descriptionFilter" placeholder="Optional">
                        </div>
                        <div class="form-group">
                            <label>Export Format:</label>
                            <select id="exportFormat">
                                <option value="json">JSON</option>
                                <option value="csv">CSV</option>
                            </select>
                        </div>
                    </div>
                    <button onclick="downloadTransactions()">Download Transactions</button>
                    <div id="transactionsResults" class="results hidden"></div>
                </div>

                <!-- Summary Statistics Section -->
                <div class="section">
                    <h2>📈 Summary Statistics</h2>
                    <button onclick="getSummary()">Get Transaction Summary</button>
                    <div id="summaryResults" class="results hidden"></div>
                </div>

                <!-- Logout Section -->
                <div class="section">
                    <h2>🚪 Session</h2>
                    <button onclick="logout()" style="background: #dc3545;">Logout</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '';

        function showStatus(message, type = 'info') {
            const statusDiv = document.getElementById('statusMessage');
            statusDiv.textContent = message;
            statusDiv.className = `status ${type}`;
            statusDiv.style.display = 'block';
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }

        function showLoading(buttonElement) {
            buttonElement.disabled = true;
            buttonElement.innerHTML = '<span class="loading"></span> Loading...';
        }

        function hideLoading(buttonElement, text) {
            buttonElement.disabled = false;
            buttonElement.textContent = text;
        }

        async function login() {
            const button = event.target;
            showLoading(button);

            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const headless = document.getElementById('headless').checked;

            try {
                const response = await fetch(`${API_BASE}/api/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, headless })
                });

                const data = await response.json();

                if (response.ok) {
                    showStatus(data.message, 'success');
                    document.getElementById('loginSection').classList.add('hidden');
                    document.getElementById('dashboard').classList.remove('hidden');
                } else {
                    showStatus(data.detail || 'Login failed', 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                hideLoading(button, 'Login to Simplifi');
            }
        }

        async function getAccounts() {
            const button = event.target;
            showLoading(button);
            const resultsDiv = document.getElementById('accountsResults');

            try {
                const response = await fetch(`${API_BASE}/api/accounts`);
                const data = await response.json();

                if (response.ok) {
                    // Safe approach to prevent XSS
                    const pre = document.createElement('pre');
                    pre.textContent = JSON.stringify(data, null, 2);
                    resultsDiv.innerHTML = '';
                    resultsDiv.appendChild(pre);
                    resultsDiv.classList.remove('hidden');
                    showStatus('Accounts loaded successfully', 'success');
                } else {
                    showStatus(data.detail || 'Failed to load accounts', 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                hideLoading(button, 'List All Accounts');
            }
        }

        async function getCategories() {
            const button = event.target;
            showLoading(button);
            const resultsDiv = document.getElementById('categoriesResults');

            try {
                const response = await fetch(`${API_BASE}/api/categories`);
                const data = await response.json();

                if (response.ok) {
                    // Safe approach to prevent XSS
                    const pre = document.createElement('pre');
                    pre.textContent = JSON.stringify(data, null, 2);
                    resultsDiv.innerHTML = '';
                    resultsDiv.appendChild(pre);
                    resultsDiv.classList.remove('hidden');
                    showStatus('Categories loaded successfully', 'success');
                } else {
                    showStatus(data.detail || 'Failed to load categories', 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                hideLoading(button, 'List All Categories');
            }
        }

        async function downloadTransactions() {
            const button = event.target;
            showLoading(button);
            const resultsDiv = document.getElementById('transactionsResults');

            const requestData = {
                last_days: parseInt(document.getElementById('lastDays').value) || null,
                start_date: document.getElementById('startDate').value || null,
                end_date: document.getElementById('endDate').value || null,
                account_id: document.getElementById('accountId').value || null,
                min_amount: parseFloat(document.getElementById('minAmount').value) || null,
                max_amount: parseFloat(document.getElementById('maxAmount').value) || null,
                category: document.getElementById('category').value || null,
                merchant: document.getElementById('merchant').value || null,
                description: document.getElementById('descriptionFilter').value || null,
                format: document.getElementById('exportFormat').value
            };

            try {
                const response = await fetch(`${API_BASE}/api/transactions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestData)
                });

                if (response.ok) {
                    const contentType = response.headers.get('content-type');

                    if (contentType.includes('application/json')) {
                        const data = await response.json();
                        // Safe approach to prevent XSS
                        const pre = document.createElement('pre');
                        pre.textContent = JSON.stringify(data, null, 2);
                        resultsDiv.innerHTML = '';
                        resultsDiv.appendChild(pre);
                        resultsDiv.classList.remove('hidden');
                        showStatus(`Downloaded ${data.transactions.length} transactions`, 'success');
                    } else if (contentType.includes('text/csv')) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `transactions_${Date.now()}.csv`;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        showStatus('CSV file downloaded', 'success');
                    }
                } else {
                    const data = await response.json();
                    showStatus(data.detail || 'Failed to download transactions', 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                hideLoading(button, 'Download Transactions');
            }
        }

        async function getSummary() {
            const button = event.target;
            showLoading(button);
            const resultsDiv = document.getElementById('summaryResults');

            const requestData = {
                last_days: parseInt(document.getElementById('lastDays').value) || 30,
                format: 'json'
            };

            try {
                const response = await fetch(`${API_BASE}/api/summary`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestData)
                });

                const data = await response.json();

                if (response.ok) {
                    // Safe approach to prevent XSS
                    const pre = document.createElement('pre');
                    pre.textContent = JSON.stringify(data, null, 2);
                    resultsDiv.innerHTML = '';
                    resultsDiv.appendChild(pre);
                    resultsDiv.classList.remove('hidden');
                    showStatus('Summary generated successfully', 'success');
                } else {
                    showStatus(data.detail || 'Failed to generate summary', 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                hideLoading(button, 'Get Transaction Summary');
            }
        }

        async function logout() {
            const button = event.target;
            showLoading(button);

            try {
                const response = await fetch(`${API_BASE}/api/logout`, {
                    method: 'POST'
                });

                const data = await response.json();

                if (response.ok) {
                    showStatus(data.message, 'success');
                    document.getElementById('loginSection').classList.remove('hidden');
                    document.getElementById('dashboard').classList.add('hidden');
                    document.getElementById('password').value = '';
                } else {
                    showStatus(data.detail || 'Logout failed', 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            } finally {
                hideLoading(button, 'Logout');
            }
        }

        // Note: Email pre-fill removed for security reasons
        // Users should enter credentials manually
    </script>
</body>
</html>
    """


@app.get("/api/status")
async def get_status(request: Request):
    """Check if user is logged in"""
    session_id = request.session.get('session_id')
    logged_in = session_id is not None and session_id in user_sessions
    return SessionStatus(
        logged_in=logged_in,
        message="Logged in" if logged_in else "Not logged in"
    )


@app.post("/api/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login(login_request: LoginRequest, request: Request):
    """Login to Quicken Simplifi"""
    try:
        # Clean up any existing session for this user
        old_session_id = request.session.get('session_id')
        if old_session_id:
            await cleanup_session(old_session_id)

        # Create new client instance
        client = SimplifiClient(
            email=login_request.email,
            password=login_request.password,
            headless=login_request.headless
        )
        await client._start_browser()

        success = await client.login()

        if success:
            # Create new session ID and store the client
            session_id = secrets.token_urlsafe(32)
            user_sessions[session_id] = client
            session_timestamps[session_id] = datetime.now()  # Track session creation
            request.session['session_id'] = session_id

            logger.info(f"Successful login for user: {login_request.email}")
            return {"message": "Login successful! Dashboard is now available."}
        else:
            await client.close()
            logger.warning(f"Failed login attempt for user: {login_request.email}")
            raise HTTPException(status_code=401, detail="Login failed. Please check credentials.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {login_request.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during login. Please try again.")


@app.get("/api/accounts")
async def get_accounts(request: Request):
    """Get list of all accounts"""
    client = await get_client_from_session(request)

    try:
        accounts = await client.get_accounts()
        return {"accounts": accounts, "count": len(accounts)}
    except Exception as e:
        logger.error(f"Error fetching accounts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching accounts.")


@app.get("/api/categories")
async def get_categories(request: Request):
    """Get list of all categories"""
    client = await get_client_from_session(request)

    try:
        # This is a placeholder - implement category fetching in SimplifiClient if needed
        return {"message": "Category listing not yet implemented in SimplifiClient", "categories": []}
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching categories.")


@app.post("/api/transactions")
async def download_transactions(transaction_request: TransactionRequest, request: Request):
    """Download and filter transactions"""
    client = await get_client_from_session(request)

    try:
        downloader = TransactionDownloader(client)

        # Download transactions
        transactions = await downloader.download_transactions(
            start_date=transaction_request.start_date,
            end_date=transaction_request.end_date,
            days=transaction_request.last_days,
            account_id=transaction_request.account_id
        )

        # Apply filters
        filtered = downloader.filter_transactions(
            transactions,
            min_amount=transaction_request.min_amount,
            max_amount=transaction_request.max_amount,
            category=transaction_request.category,
            merchant=transaction_request.merchant,
            description=transaction_request.description
        )

        # Export based on format
        if transaction_request.format.lower() == 'csv':
            filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            downloader.export_to_csv(filtered, filename)
            return FileResponse(
                filename,
                media_type="text/csv",
                filename=filename
            )
        else:
            return {
                "transactions": filtered,
                "count": len(filtered),
                "filters_applied": {
                    "start_date": transaction_request.start_date,
                    "end_date": transaction_request.end_date,
                    "last_days": transaction_request.last_days,
                    "account_id": transaction_request.account_id,
                    "min_amount": transaction_request.min_amount,
                    "max_amount": transaction_request.max_amount,
                    "category": transaction_request.category,
                    "merchant": transaction_request.merchant,
                    "description": transaction_request.description
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading transactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while downloading transactions.")


@app.post("/api/summary")
async def get_summary(transaction_request: TransactionRequest, request: Request):
    """Get transaction summary statistics"""
    client = await get_client_from_session(request)

    try:
        downloader = TransactionDownloader(client)

        # Download transactions
        transactions = await downloader.download_transactions(
            start_date=transaction_request.start_date,
            end_date=transaction_request.end_date,
            days=transaction_request.last_days,
            account_id=transaction_request.account_id
        )

        # Apply filters
        filtered = downloader.filter_transactions(
            transactions,
            min_amount=transaction_request.min_amount,
            max_amount=transaction_request.max_amount,
            category=transaction_request.category,
            merchant=transaction_request.merchant,
            description=transaction_request.description
        )

        # Get summary
        summary = downloader.get_summary_statistics(filtered)

        return {
            "summary": summary,
            "transaction_count": len(filtered),
            "date_range": {
                "start": transaction_request.start_date or f"Last {transaction_request.last_days} days",
                "end": transaction_request.end_date or "Today"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while generating summary.")


@app.post("/api/reports")
async def generate_report(report_request: ReportRequest, request: Request):
    """Generate financial reports"""
    client = await get_client_from_session(request)

    try:
        downloader = TransactionDownloader(client)

        # Download transactions
        transactions = await downloader.download_transactions(
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            days=report_request.last_days
        )

        if not transactions:
            return {
                "report_type": report_request.report_type,
                "error": "No transactions found",
                "data": None
            }

        # Build filters
        filters = ReportFilter(
            start_date=report_request.start_date,
            end_date=report_request.end_date,
            min_amount=report_request.min_amount,
            max_amount=report_request.max_amount,
            categories=report_request.categories,
            exclude_categories=report_request.exclude_categories,
            merchants=report_request.merchants,
            exclude_merchants=report_request.exclude_merchants,
            accounts=report_request.accounts,
            description_contains=report_request.description_contains,
            notes_contains=report_request.notes_contains
        )

        # Initialize report builder
        builder = ReportBuilder(transactions)

        # Map grouping string to enum
        grouping_map = {
            'daily': TimeGrouping.DAILY,
            'weekly': TimeGrouping.WEEKLY,
            'monthly': TimeGrouping.MONTHLY,
            'quarterly': TimeGrouping.QUARTERLY,
            'yearly': TimeGrouping.YEARLY
        }
        grouping = grouping_map.get(report_request.grouping, TimeGrouping.MONTHLY)

        # Generate appropriate report
        report_data = None

        if report_request.report_type == 'profit_loss':
            report = builder.profit_and_loss(filters)
            report_data = report.to_dict()

        elif report_request.report_type == 'cash_flow':
            report = builder.cash_flow(filters, grouping)
            report_data = report.to_dict()

        elif report_request.report_type == 'category_analysis':
            report = builder.category_analysis(filters, report_request.top_n)
            report_data = report.to_dict()

        elif report_request.report_type == 'merchant_analysis':
            top_n = report_request.top_n or 20
            report = builder.merchant_analysis(filters, top_n)
            report_data = report.to_dict()

        elif report_request.report_type == 'trend_analysis':
            report = builder.trend_analysis(filters, grouping)
            report_data = report.to_dict()

        elif report_request.report_type == 'account_summary':
            report = builder.account_summary(filters)
            report_data = report.to_dict()

        return {
            "report_type": report_request.report_type,
            "data": report_data,
            "filters_applied": {
                "start_date": report_request.start_date,
                "end_date": report_request.end_date,
                "last_days": report_request.last_days,
                "min_amount": report_request.min_amount,
                "max_amount": report_request.max_amount,
                "categories": report_request.categories,
                "exclude_categories": report_request.exclude_categories,
                "grouping": report_request.grouping,
                "top_n": report_request.top_n
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the report: {str(e)}")


@app.post("/api/logout")
async def logout(request: Request):
    """Logout and close browser"""
    try:
        session_id = request.session.get('session_id')
        if session_id:
            await cleanup_session(session_id)
            request.session.clear()
            logger.info(f"User logged out successfully")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during logout.")


if __name__ == "__main__":
    print("🚀 Starting Quicken Simplifi Web Application...")
    print("📍 Open your browser to: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("⚡ Press CTRL+C to stop the server")

    uvicorn.run(app, host="0.0.0.0", port=8000)
