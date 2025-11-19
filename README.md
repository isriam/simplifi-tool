# Quicken Simplifi Transaction Downloader

A Python application to download, parse, and export transactions from Quicken Simplifi. This tool allows you to programmatically access your financial data over specific time ranges and export it to CSV or JSON formats.

## Features

- **Authentication**: Secure login to Quicken Simplifi with token-based authentication
- **Transaction Download**: Download transactions over custom date ranges
- **Flexible Filtering**: Filter by amount, category, merchant, description, and account
- **Multiple Export Formats**: Export to CSV or JSON
- **Summary Statistics**: Generate financial summaries and breakdowns
- **Account Management**: List all accounts and categories
- **Date Range Options**: Download by specific dates or last N days
- **Web Interface**: Modern web dashboard for easy access to all features

## Web Application

For the easiest experience, use the **web interface** instead of the command-line tools!

### Quick Start

1. Run the setup script:
```bash
./setup.sh
```

2. Start the web application:
```bash
./run_webapp.sh
```

3. Open your browser to: **http://localhost:8000**

### Features

The web interface provides a beautiful, user-friendly dashboard with:

- **One-Click Login**: Easy authentication with optional headless mode
- **Visual Dashboard**: All features accessible from a single page
- **Account Explorer**: Browse all your accounts with one click
- **Category Browser**: View all transaction categories
- **Advanced Filtering**: Filter transactions by date, amount, category, merchant, and more
- **Export Options**: Download as JSON or CSV directly from the browser
- **Summary Statistics**: Get instant financial summaries and breakdowns
- **No Command Line**: Everything through an intuitive web interface

### Web Interface Screenshots

The web app includes:
- Clean, modern design with gradient styling
- Responsive layout that works on mobile and desktop
- Real-time status updates and error handling
- Loading indicators for all operations
- JSON preview in the browser or CSV downloads

### API Documentation

The web app also provides automatic API documentation at: **http://localhost:8000/docs**

You can use the API endpoints programmatically if needed.

## Installation

### Prerequisites

- Python 3.7 or higher
- Quicken Simplifi account

### Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd testing
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Configure your credentials:
```bash
cp .env.example .env
```

5. Edit `.env` and add your Quicken Simplifi credentials:
```
SIMPLIFI_EMAIL=your_email@example.com
SIMPLIFI_PASSWORD=your_password_here
```

**Note**: The `.env` file is gitignored to protect your credentials.

### Important: Browser Automation

This application uses **Playwright** for browser automation to interact with Quicken Simplifi. All code is self-contained with **no third-party API dependencies** - the app simply automates a real browser just like you would use manually. This gives you complete control and transparency over how your data is accessed.

## Usage

**Recommended**: Use the web interface (see [Web Application](#web-application) section above) for the easiest experience!

For command-line usage, continue below:

### Basic Usage

Download last 30 days of transactions to CSV:
```bash
python main.py --output transactions.csv
```

**For 2FA accounts**: Use `--show-browser` to see the browser window and complete 2FA manually:
```bash
python main.py --show-browser --output transactions.csv
```

### Date Range Options

Download transactions for a specific date range:
```bash
python main.py --start-date 2024-01-01 --end-date 2024-12-31 --format json
```

Download last 90 days:
```bash
python main.py --days 90
```

### Filtering Transactions

Filter by minimum amount:
```bash
python main.py --min-amount 100 --output large_transactions.csv
```

Filter by category:
```bash
python main.py --category "Groceries" --days 30
```

Filter by merchant:
```bash
python main.py --merchant "Amazon" --days 60
```

Combine multiple filters:
```bash
python main.py --days 30 --min-amount 50 --max-amount 500 --category "Dining"
```

### Account Operations

List all accounts:
```bash
python main.py --list-accounts
```

Download from specific account:
```bash
python main.py --account-id 12345 --days 60
```

List all categories:
```bash
python main.py --list-categories
```

### Summary Statistics

Get transaction summary with statistics:
```bash
python main.py --summary --days 30
```

Output includes:
- Total transactions count
- Total amount
- Average, median, min, max amounts
- Breakdown by category

### Export Formats

Export to CSV (default):
```bash
python main.py --days 30 --format csv --output my_transactions.csv
```

Export to JSON with pretty printing:
```bash
python main.py --days 30 --format json --pretty --output my_transactions.json
```

### Advanced Examples

Download all transactions from 2024, filter for amounts over $1000, and generate summary:
```bash
python main.py --start-date 2024-01-01 --end-date 2024-12-31 \
  --min-amount 1000 --summary --format json --pretty
```

Download last 7 days from specific account with category filter:
```bash
python main.py --days 7 --account-id 12345 --category "Shopping" \
  --output weekly_shopping.csv
```

## Command-Line Options

### Authentication
- `--email`: Simplifi account email (or set SIMPLIFI_EMAIL env var)
- `--password`: Simplifi account password (or set SIMPLIFI_PASSWORD env var)
- `--show-browser`: Show browser window (useful for debugging and completing 2FA)
- `--headless`: Run browser in headless mode (default: True)

### Date Range
- `--start-date`: Start date in YYYY-MM-DD format
- `--end-date`: End date in YYYY-MM-DD format (defaults to today)
- `--days`: Download transactions from the last N days

### Filters
- `--account-id`: Filter by specific account ID
- `--min-amount`: Minimum transaction amount
- `--max-amount`: Maximum transaction amount
- `--category`: Filter by category name
- `--merchant`: Filter by merchant name
- `--description`: Filter by description (partial match)
- `--limit`: Maximum number of transactions to retrieve

### Output
- `--output`: Output filename (auto-generated if not specified)
- `--format`: Output format - csv or json (default: csv)
- `--pretty`: Pretty print JSON output

### Actions
- `--list-accounts`: List all accounts and exit
- `--list-categories`: List all categories and exit
- `--summary`: Display transaction summary statistics

## Project Structure

```
.
├── webapp.py                  # FastAPI web application (recommended)
├── run_webapp.sh             # Web app startup script
├── main.py                    # CLI entry point
├── simplifi_client.py         # Quicken Simplifi API client
├── transaction_downloader.py  # Transaction download and parsing logic
├── example_usage.py          # Usage examples
├── requirements.txt           # Python dependencies
├── setup.sh                  # Setup script
├── .env.example              # Example environment configuration
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## How It Works

### Architecture

1. **SimplifiClient** (`simplifi_client.py`):
   - Handles authentication with Quicken Simplifi
   - Manages API requests for accounts, transactions, categories, and tags
   - Maintains session state and authentication tokens

2. **TransactionDownloader** (`transaction_downloader.py`):
   - Downloads transactions using the SimplifiClient
   - Filters transactions based on various criteria
   - Parses transactions into pandas DataFrames
   - Exports data to CSV or JSON formats
   - Generates summary statistics

3. **Main CLI** (`main.py`):
   - Command-line interface for easy interaction
   - Orchestrates authentication, download, filtering, and export operations
   - Provides user-friendly output and error handling

### Browser Automation Details

This application uses Playwright browser automation to interact with Quicken Simplifi:

- **No unofficial APIs**: The app controls a real Chromium browser to access Simplifi
- **Complete transparency**: All code is self-contained - no hidden third-party dependencies
- **Same as manual access**: The automation does exactly what you would do manually
- **Security**: Your credentials are only used to log in through the official Simplifi login page
- **Headless mode**: Runs without showing the browser window by default (use `--show-browser` to see it)

**Note**: Since this automates the web interface, functionality may change if Quicken updates their website layout. The HTML selectors may need adjustment.

## Security Considerations

- **Never commit your `.env` file** - it contains your credentials
- Store credentials securely and use environment variables
- Consider using a dedicated application password if your account supports it
- The application uses HTTPS for all API communications
- Tokens are stored only in memory during execution

## Troubleshooting

### Authentication Fails
- Verify your email and password in `.env`
- If 2FA is enabled, use `--show-browser` to complete verification manually
- Ensure you have an active Quicken Simplifi subscription
- Make sure Playwright browsers are installed: `playwright install chromium`

### No Transactions Returned
- Verify the date range includes transactions
- Check if the account ID is correct
- Try without filters first to see all available data

### Scraping Errors
- The web interface may have changed - selectors may need updating
- Network issues may cause timeouts - try again
- Use `--show-browser` to see what's happening in the browser
- Take screenshots for debugging: the app can save screenshots during execution

## Limitations

- This is an **unofficial** tool not endorsed by Quicken
- Web interface selectors may need updates if Quicken changes their site
- Two-factor authentication requires `--show-browser` for manual completion
- HTML parsing depends on Simplifi's current page structure
- Slower than a direct API (but no third-party dependencies!)
- Requires Playwright browsers to be installed

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for personal use. Please respect Quicken Simplifi's Terms of Service when using this tool.

## Disclaimer

This is an unofficial tool and is not affiliated with, endorsed by, or connected to Quicken Inc. or Simplifi. Use at your own risk. The authors are not responsible for any issues that may arise from using this tool, including but not limited to account access issues or data loss.

## Future Enhancements

Potential features for future development:
- Auto-detect and update HTML selectors
- Session caching to avoid repeated logins
- Transaction categorization and analysis
- Budget tracking and alerts
- Multi-account reconciliation
- Recurring transaction detection
- Spending trend visualization with charts
- Export to other formats (Excel, PDF)
- Parallel account processing
- Smart selector fallbacks
- Enhanced web interface with charts and graphs
- Real-time transaction monitoring
- Automated reporting and scheduled exports

## Support

For issues, questions, or feature requests, please open an issue in the repository.
