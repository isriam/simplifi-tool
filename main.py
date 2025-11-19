#!/usr/bin/env python3
"""
Quicken Simplifi Transaction Downloader CLI
Main entry point for the application
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from simplifi_client import SimplifiClient
from transaction_downloader import TransactionDownloader


def main():
    """Main CLI entry point"""

    # Load environment variables
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Download and parse transactions from Quicken Simplifi',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download last 30 days of transactions to CSV
  python main.py --output transactions.csv

  # Download specific date range
  python main.py --start-date 2024-01-01 --end-date 2024-12-31 --format json

  # Download last 90 days
  python main.py --days 90

  # Download and filter by minimum amount
  python main.py --min-amount 100

  # List all accounts
  python main.py --list-accounts

  # Get transaction summary
  python main.py --summary --days 30

  # Download from specific account
  python main.py --account-id 12345 --days 60
        """
    )

    # Authentication
    auth_group = parser.add_argument_group('authentication')
    auth_group.add_argument(
        '--email',
        help='Simplifi account email (or set SIMPLIFI_EMAIL env var)'
    )
    auth_group.add_argument(
        '--password',
        help='Simplifi account password (or set SIMPLIFI_PASSWORD env var)'
    )
    auth_group.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True)'
    )
    auth_group.add_argument(
        '--show-browser',
        action='store_true',
        help='Show browser window (useful for debugging and 2FA)'
    )

    # Date range options
    date_group = parser.add_argument_group('date range')
    date_group.add_argument(
        '--start-date',
        help='Start date in YYYY-MM-DD format'
    )
    date_group.add_argument(
        '--end-date',
        help='End date in YYYY-MM-DD format (defaults to today)'
    )
    date_group.add_argument(
        '--days',
        type=int,
        help='Download transactions from the last N days'
    )

    # Filter options
    filter_group = parser.add_argument_group('filters')
    filter_group.add_argument(
        '--account-id',
        help='Filter by specific account ID'
    )
    filter_group.add_argument(
        '--min-amount',
        type=float,
        help='Minimum transaction amount'
    )
    filter_group.add_argument(
        '--max-amount',
        type=float,
        help='Maximum transaction amount'
    )
    filter_group.add_argument(
        '--category',
        help='Filter by category name'
    )
    filter_group.add_argument(
        '--merchant',
        help='Filter by merchant name'
    )
    filter_group.add_argument(
        '--description',
        help='Filter by description (partial match)'
    )

    # Output options
    output_group = parser.add_argument_group('output')
    output_group.add_argument(
        '--output',
        help='Output filename (auto-generated if not specified)'
    )
    output_group.add_argument(
        '--format',
        choices=['csv', 'json'],
        default='csv',
        help='Output format (default: csv)'
    )
    output_group.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty print JSON output'
    )

    # Actions
    action_group = parser.add_argument_group('actions')
    action_group.add_argument(
        '--list-accounts',
        action='store_true',
        help='List all accounts and exit'
    )
    action_group.add_argument(
        '--list-categories',
        action='store_true',
        help='List all categories and exit'
    )
    action_group.add_argument(
        '--summary',
        action='store_true',
        help='Display transaction summary statistics'
    )

    args = parser.parse_args()

    # Initialize client with browser automation
    # Use headless mode unless --show-browser is specified
    headless_mode = not args.show_browser

    try:
        with SimplifiClient(email=args.email, password=args.password, headless=headless_mode) as client:
            print("Authenticating with Quicken Simplifi...")
            if not client.login():
                print("ERROR: Authentication failed. Please check your credentials.")
                print("If you have 2FA enabled, use --show-browser to complete verification.")
                sys.exit(1)

            print("Authentication successful!")
            run_commands(client, args)

    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_commands(client: SimplifiClient, args):
    """Execute the requested commands"""
    try:

        # Handle list accounts action
        if args.list_accounts:
            print("\nRetrieving accounts...")
            accounts = client.get_accounts()
            if accounts:
                print(f"\nFound {len(accounts)} account(s):")
                for account in accounts:
                    print(f"  - {account.get('name', 'N/A')} (ID: {account.get('id', 'N/A')})")
                    print(f"    Balance: ${account.get('balance', 0):.2f}")
                    print(f"    Type: {account.get('type', 'N/A')}")
            else:
                print("No accounts found or unable to retrieve accounts.")
            return

        # Handle list categories action
        if args.list_categories:
            print("\nRetrieving categories...")
            categories = client.get_categories()
            if categories:
                print(f"\nFound {len(categories)} category(ies):")
                for category in categories:
                    print(f"  - {category.get('name', 'N/A')} (ID: {category.get('id', 'N/A')})")
            else:
                print("No categories found or unable to retrieve categories.")
            return

        # Calculate date range
        start_date = args.start_date
        end_date = args.end_date

        if args.days:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start = datetime.now() - timedelta(days=args.days)
            start_date = start.strftime('%Y-%m-%d')

        # Download transactions
        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(
            start_date=start_date,
            end_date=end_date,
            account_id=args.account_id,
            days=args.days
        )

        if not transactions:
            print("No transactions found for the specified criteria.")
            return

        # Apply filters
        if any([args.min_amount, args.max_amount, args.category, args.merchant, args.description]):
            print("\nApplying filters...")
            original_count = len(transactions)
            transactions = downloader.filter_transactions(
                transactions,
                min_amount=args.min_amount,
                max_amount=args.max_amount,
                category=args.category,
                merchant=args.merchant,
                description=args.description
            )
            print(f"Filtered from {original_count} to {len(transactions)} transactions")

        # Display summary if requested
        if args.summary:
            print("\n" + "="*50)
            print("TRANSACTION SUMMARY")
            print("="*50)
            stats = downloader.get_summary_statistics(transactions)
            print(f"Total Transactions: {stats.get('total_transactions', 0)}")
            print(f"Total Amount: ${stats.get('total_amount', 0):.2f}")
            print(f"Average Amount: ${stats.get('average_amount', 0):.2f}")
            print(f"Median Amount: ${stats.get('median_amount', 0):.2f}")
            print(f"Min Amount: ${stats.get('min_amount', 0):.2f}")
            print(f"Max Amount: ${stats.get('max_amount', 0):.2f}")

            if 'by_category' in stats:
                print("\nBreakdown by Category:")
                for category, values in stats['by_category'].items():
                    print(f"  {category}:")
                    print(f"    Total: ${values.get('total', 0):.2f}")
                    print(f"    Count: {values.get('count', 0)}")
            print("="*50 + "\n")

        # Export transactions
        if args.format == 'csv':
            output_file = downloader.export_to_csv(transactions, args.output)
        else:  # json
            output_file = downloader.export_to_json(
                transactions,
                args.output,
                pretty=args.pretty
            )

        print(f"\nSuccess! Transactions saved to: {output_file}")

    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == '__main__':
    main()
