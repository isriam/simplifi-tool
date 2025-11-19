#!/usr/bin/env python3
"""
Example usage of the Quicken Simplifi Transaction Downloader
This demonstrates how to use the modules programmatically
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from simplifi_client import SimplifiClient
from transaction_downloader import TransactionDownloader


def example_basic_download():
    """Example: Basic transaction download using browser automation"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Transaction Download")
    print("="*60)

    # Load credentials from .env file
    load_dotenv()

    # Initialize and authenticate using context manager
    # Use headless=False to see the browser (useful for debugging)
    with SimplifiClient(headless=True) as client:
        print("Authenticating...")

        if client.login():
            print("✓ Authentication successful")

            # Create downloader
            downloader = TransactionDownloader(client)

            # Download last 30 days
            transactions = downloader.download_transactions(days=30)

            # Export to CSV
            if transactions:
                filename = downloader.export_to_csv(transactions)
                print(f"✓ Exported {len(transactions)} transactions to {filename}")
        else:
            print("✗ Authentication failed")


def example_date_range_filter():
    """Example: Download with specific date range and filters"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Date Range and Amount Filtering")
    print("="*60)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if client.login():
            print("✓ Authentication successful")

            downloader = TransactionDownloader(client)

            # Define date range
            start_date = "2024-01-01"
            end_date = "2024-12-31"

            # Download transactions
            transactions = downloader.download_transactions(
                start_date=start_date,
                end_date=end_date
            )

            # Filter for large transactions
            large_transactions = downloader.filter_transactions(
                transactions,
                min_amount=500
            )

            print(f"✓ Found {len(large_transactions)} transactions over $500")

            # Export to JSON
            if large_transactions:
                filename = downloader.export_to_json(
                    large_transactions,
                    "large_transactions.json",
                    pretty=True
                )
                print(f"✓ Exported to {filename}")


def example_category_analysis():
    """Example: Analyze spending by category"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Category Analysis")
    print("="*60)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if client.login():
            print("✓ Authentication successful")

            downloader = TransactionDownloader(client)

            # Download last 90 days
            transactions = downloader.download_transactions(days=90)

            # Get summary statistics
            stats = downloader.get_summary_statistics(transactions)

            print(f"\nTransaction Summary (Last 90 Days):")
            print(f"  Total Transactions: {stats['total_transactions']}")
            print(f"  Total Amount: ${stats['total_amount']:.2f}")
            print(f"  Average: ${stats['average_amount']:.2f}")
            print(f"  Median: ${stats['median_amount']:.2f}")

            if 'by_category' in stats:
                print(f"\n  Top Categories:")
                # Sort by total amount
                categories = sorted(
                    stats['by_category'].items(),
                    key=lambda x: x[1]['total'],
                    reverse=True
                )
                for i, (category, data) in enumerate(categories[:5], 1):
                    print(f"    {i}. {category}: ${data['total']:.2f} ({data['count']} transactions)")


def example_account_specific():
    """Example: Download from specific account"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Account-Specific Download")
    print("="*60)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if client.login():
            print("✓ Authentication successful")

            # List all accounts
            accounts = client.get_accounts()
            print(f"\n✓ Found {len(accounts)} account(s):")

            for i, account in enumerate(accounts, 1):
                print(f"  {i}. {account.get('name', 'N/A')}")
                print(f"     ID: {account.get('id', 'N/A')}")
                print(f"     Balance: ${account.get('balance', 0):.2f}")

            # Download from first account (as example)
            if accounts:
                account_id = accounts[0].get('id')
                downloader = TransactionDownloader(client)

                transactions = downloader.download_transactions(
                    account_id=account_id,
                    days=30
                )

                print(f"\n✓ Downloaded {len(transactions)} transactions from {accounts[0].get('name')}")


def example_merchant_filter():
    """Example: Filter by merchant"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Merchant Filtering")
    print("="*60)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if client.login():
            print("✓ Authentication successful")

            downloader = TransactionDownloader(client)

            # Download last 60 days
            transactions = downloader.download_transactions(days=60)

            # Filter for Amazon transactions
            amazon_transactions = downloader.filter_transactions(
                transactions,
                merchant="Amazon"
            )

            print(f"✓ Found {len(amazon_transactions)} Amazon transactions")

            # Calculate total spent at Amazon
            if amazon_transactions:
                total = sum(t.get('amount', 0) for t in amazon_transactions)
                print(f"  Total spent: ${total:.2f}")

                # Export
                downloader.export_to_csv(amazon_transactions, "amazon_transactions.csv")


def example_dataframe_analysis():
    """Example: Using pandas DataFrame for analysis"""
    print("\n" + "="*60)
    print("EXAMPLE 6: DataFrame Analysis")
    print("="*60)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if client.login():
            print("✓ Authentication successful")

            downloader = TransactionDownloader(client)
            transactions = downloader.download_transactions(days=30)

            # Convert to DataFrame
            df = downloader.parse_transactions(transactions)

            if not df.empty:
                print(f"\n✓ Loaded {len(df)} transactions into DataFrame")
                print(f"\nDataFrame Info:")
                print(f"  Columns: {', '.join(df.columns.tolist())}")
                print(f"\nFirst 5 transactions:")
                print(df.head())

                # Perform pandas operations
                if 'amount' in df.columns:
                    print(f"\nAmount Statistics:")
                    print(df['amount'].describe())


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("Quicken Simplifi Transaction Downloader - Usage Examples")
    print("="*60)

    examples = [
        ("Basic Download", example_basic_download),
        ("Date Range Filter", example_date_range_filter),
        ("Category Analysis", example_category_analysis),
        ("Account Specific", example_account_specific),
        ("Merchant Filter", example_merchant_filter),
        ("DataFrame Analysis", example_dataframe_analysis),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning Example 1 (Basic Download)...")
    print("To run other examples, modify the main() function\n")

    # Run the first example by default
    example_basic_download()

    print("\n" + "="*60)
    print("Example completed!")
    print("="*60)
    print("\nTo run other examples:")
    print("  - Uncomment the desired example function call in main()")
    print("  - Or call the example function directly")
    print("\n")


if __name__ == '__main__':
    main()
