"""
Transaction Downloader and Parser for Quicken Simplifi
Handles downloading, filtering, and exporting transactions
"""

import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from simplifi_client import SimplifiClient


class TransactionDownloader:
    """Downloads and processes transactions from Quicken Simplifi"""

    def __init__(self, client: SimplifiClient):
        """
        Initialize the transaction downloader

        Args:
            client: Authenticated SimplifiClient instance
        """
        self.client = client

    async def download_transactions(self,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             account_id: Optional[str] = None,
                             days: Optional[int] = None) -> List[Dict]:
        """
        Download transactions from Simplifi using browser automation

        Args:
            start_date: Start date in YYYY-MM-DD format (defaults to 30 days ago)
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_id: Optional account ID to filter transactions
            days: Number of days back from today (alternative to start_date)

        Returns:
            List of transaction dictionaries
        """
        # Set default date range if not provided
        if days:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start = datetime.now() - timedelta(days=days)
            start_date = start.strftime('%Y-%m-%d')
        else:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            if not start_date:
                # Default to 30 days ago
                start = datetime.now() - timedelta(days=30)
                start_date = start.strftime('%Y-%m-%d')

        print(f"Downloading transactions from {start_date} to {end_date}...")

        transactions = await self.client.get_transactions(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )

        print(f"Downloaded {len(transactions)} transactions")
        return transactions

    def filter_transactions(self,
                          transactions: List[Dict],
                          min_amount: Optional[float] = None,
                          max_amount: Optional[float] = None,
                          category: Optional[str] = None,
                          merchant: Optional[str] = None,
                          description: Optional[str] = None) -> List[Dict]:
        """
        Filter transactions based on criteria

        Args:
            transactions: List of transaction dictionaries
            min_amount: Minimum transaction amount
            max_amount: Maximum transaction amount
            category: Filter by category name (case-insensitive)
            merchant: Filter by merchant name (case-insensitive)
            description: Filter by description (case-insensitive, partial match)

        Returns:
            Filtered list of transactions
        """
        filtered = transactions

        if min_amount is not None:
            filtered = [t for t in filtered if t.get('amount', 0) >= min_amount]

        if max_amount is not None:
            filtered = [t for t in filtered if t.get('amount', 0) <= max_amount]

        if category:
            filtered = [
                t for t in filtered
                if t.get('category', '').lower() == category.lower()
            ]

        if merchant:
            filtered = [
                t for t in filtered
                if merchant.lower() in t.get('merchant', '').lower()
            ]

        if description:
            filtered = [
                t for t in filtered
                if description.lower() in t.get('description', '').lower()
            ]

        return filtered

    def parse_transactions(self, transactions: List[Dict]) -> pd.DataFrame:
        """
        Parse transactions into a pandas DataFrame for easier analysis

        Args:
            transactions: List of transaction dictionaries

        Returns:
            DataFrame with transaction data
        """
        if not transactions:
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(transactions)

        # Convert date columns if present
        date_columns = ['date', 'postedDate', 'transactionDate']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Convert amount to numeric if present
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        return df

    def export_to_csv(self,
                     transactions: List[Dict],
                     filename: str = None) -> str:
        """
        Export transactions to CSV file

        Args:
            transactions: List of transaction dictionaries
            filename: Output filename (auto-generated if not provided)

        Returns:
            Path to the created CSV file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"transactions_{timestamp}.csv"

        if not transactions:
            print("No transactions to export")
            return filename

        # Convert to DataFrame for better CSV export
        df = self.parse_transactions(transactions)

        df.to_csv(filename, index=False)
        print(f"Exported {len(transactions)} transactions to {filename}")

        return filename

    def export_to_json(self,
                      transactions: List[Dict],
                      filename: str = None,
                      pretty: bool = True) -> str:
        """
        Export transactions to JSON file

        Args:
            transactions: List of transaction dictionaries
            filename: Output filename (auto-generated if not provided)
            pretty: If True, format JSON with indentation

        Returns:
            Path to the created JSON file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"transactions_{timestamp}.json"

        with open(filename, 'w') as f:
            if pretty:
                json.dump(transactions, f, indent=2, default=str)
            else:
                json.dump(transactions, f, default=str)

        print(f"Exported {len(transactions)} transactions to {filename}")
        return filename

    def get_summary_statistics(self, transactions: List[Dict]) -> Dict:
        """
        Generate summary statistics for transactions

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with summary statistics
        """
        if not transactions:
            return {
                'total_transactions': 0,
                'total_amount': 0,
                'average_amount': 0,
                'min_amount': 0,
                'max_amount': 0
            }

        df = self.parse_transactions(transactions)

        if 'amount' not in df.columns:
            return {'error': 'No amount field found in transactions'}

        stats = {
            'total_transactions': len(transactions),
            'total_amount': float(df['amount'].sum()),
            'average_amount': float(df['amount'].mean()),
            'min_amount': float(df['amount'].min()),
            'max_amount': float(df['amount'].max()),
            'median_amount': float(df['amount'].median())
        }

        # Add category breakdown if available
        if 'category' in df.columns:
            stats['by_category'] = df.groupby('category')['amount'].agg([
                ('total', 'sum'),
                ('count', 'size')
            ]).to_dict()

        return stats
