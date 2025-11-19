"""
FastAPI Web Application for Quicken Simplifi Transaction Downloader
Provides a web interface to run all Python scripts and functions.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import json
import uvicorn
from dotenv import load_dotenv

from simplifi_client import SimplifiClient
from transaction_downloader import TransactionDownloader

# Load environment variables
load_dotenv()

app = FastAPI(title="Quicken Simplifi Transaction Downloader", version="1.0.0")

# Global client instance (will be initialized on login)
client_instance = None


class LoginRequest(BaseModel):
    email: str
    password: str
    headless: bool = True


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
    format: str = "json"  # json or csv


class SessionStatus(BaseModel):
    logged_in: bool
    message: str


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
                    resultsDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
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
                    resultsDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
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
                        resultsDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
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
                    resultsDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
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

        // Load email from env if available
        window.addEventListener('DOMContentLoaded', async () => {
            const envEmail = '""" + os.getenv('SIMPLIFI_EMAIL', '') + """';
            if (envEmail) {
                document.getElementById('email').value = envEmail;
            }
        });
    </script>
</body>
</html>
    """


@app.get("/api/status")
async def get_status():
    """Check if user is logged in"""
    global client_instance
    return SessionStatus(
        logged_in=client_instance is not None,
        message="Logged in" if client_instance else "Not logged in"
    )


@app.post("/api/login")
async def login(request: LoginRequest):
    """Login to Quicken Simplifi"""
    global client_instance

    try:
        if client_instance:
            client_instance.close()

        client_instance = SimplifiClient(headless=request.headless)
        client_instance._start_browser()

        success = client_instance.login(request.email, request.password)

        if success:
            return {"message": "Login successful! Dashboard is now available."}
        else:
            client_instance = None
            raise HTTPException(status_code=401, detail="Login failed. Please check credentials.")

    except Exception as e:
        client_instance = None
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@app.get("/api/accounts")
async def get_accounts():
    """Get list of all accounts"""
    global client_instance

    if not client_instance:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        accounts = client_instance.get_accounts()
        return {"accounts": accounts, "count": len(accounts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching accounts: {str(e)}")


@app.get("/api/categories")
async def get_categories():
    """Get list of all categories"""
    global client_instance

    if not client_instance:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        # This is a placeholder - implement category fetching in SimplifiClient if needed
        return {"message": "Category listing not yet implemented in SimplifiClient", "categories": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")


@app.post("/api/transactions")
async def download_transactions(request: TransactionRequest):
    """Download and filter transactions"""
    global client_instance

    if not client_instance:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        downloader = TransactionDownloader(client_instance)

        # Download transactions
        transactions = downloader.download_transactions(
            start_date=request.start_date,
            end_date=request.end_date,
            last_days=request.last_days,
            account_id=request.account_id
        )

        # Apply filters
        filtered = downloader.filter_transactions(
            transactions,
            min_amount=request.min_amount,
            max_amount=request.max_amount,
            category=request.category,
            merchant=request.merchant,
            description=request.description
        )

        # Export based on format
        if request.format.lower() == 'csv':
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
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "last_days": request.last_days,
                    "account_id": request.account_id,
                    "min_amount": request.min_amount,
                    "max_amount": request.max_amount,
                    "category": request.category,
                    "merchant": request.merchant,
                    "description": request.description
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading transactions: {str(e)}")


@app.post("/api/summary")
async def get_summary(request: TransactionRequest):
    """Get transaction summary statistics"""
    global client_instance

    if not client_instance:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        downloader = TransactionDownloader(client_instance)

        # Download transactions
        transactions = downloader.download_transactions(
            start_date=request.start_date,
            end_date=request.end_date,
            last_days=request.last_days,
            account_id=request.account_id
        )

        # Apply filters
        filtered = downloader.filter_transactions(
            transactions,
            min_amount=request.min_amount,
            max_amount=request.max_amount,
            category=request.category,
            merchant=request.merchant,
            description=request.description
        )

        # Get summary
        summary = downloader.get_summary_statistics(filtered)

        return {
            "summary": summary,
            "transaction_count": len(filtered),
            "date_range": {
                "start": request.start_date or f"Last {request.last_days} days",
                "end": request.end_date or "Today"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@app.post("/api/logout")
async def logout():
    """Logout and close browser"""
    global client_instance

    try:
        if client_instance:
            client_instance.close()
            client_instance = None
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during logout: {str(e)}")


if __name__ == "__main__":
    print("🚀 Starting Quicken Simplifi Web Application...")
    print("📍 Open your browser to: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("⚡ Press CTRL+C to stop the server")

    uvicorn.run(app, host="0.0.0.0", port=8000)
