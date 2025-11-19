"""
Financial Report Builder for Simplifi Transaction Data

This module provides comprehensive report generation capabilities including:
- Profit & Loss (P&L) Reports
- Cash Flow Reports
- Category Analysis Reports
- Trend Analysis Reports
- Custom Reports with flexible filtering and sorting

Author: Financial Report Builder
Date: 2025-11-19
"""

import pandas as pd
import json
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict


class ReportType(Enum):
    """Supported report types"""
    PROFIT_AND_LOSS = "profit_and_loss"
    CASH_FLOW = "cash_flow"
    CATEGORY_ANALYSIS = "category_analysis"
    TREND_ANALYSIS = "trend_analysis"
    MERCHANT_ANALYSIS = "merchant_analysis"
    ACCOUNT_SUMMARY = "account_summary"
    CUSTOM = "custom"


class SortOrder(Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class TimeGrouping(Enum):
    """Time-based grouping options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class ReportFilter:
    """Filter configuration for reports"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    categories: Optional[List[str]] = None
    merchants: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    description_contains: Optional[str] = None
    notes_contains: Optional[str] = None
    exclude_categories: Optional[List[str]] = None
    exclude_merchants: Optional[List[str]] = None


@dataclass
class ReportSort:
    """Sort configuration for reports"""
    field: str
    order: SortOrder = SortOrder.DESC


class BaseReport:
    """Base class for all report types"""

    def __init__(self, transactions: List[Dict]):
        """
        Initialize report with transaction data

        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = transactions
        self.df = self._to_dataframe(transactions)

    def _to_dataframe(self, transactions: List[Dict]) -> pd.DataFrame:
        """Convert transactions to pandas DataFrame"""
        if not transactions:
            return pd.DataFrame()

        df = pd.DataFrame(transactions)

        # Convert date columns
        date_columns = ['date', 'postedDate', 'transactionDate']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Convert amount to numeric
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        return df

    def apply_filters(self, filters: ReportFilter) -> pd.DataFrame:
        """
        Apply filters to the transaction DataFrame

        Args:
            filters: ReportFilter object with filter criteria

        Returns:
            Filtered DataFrame
        """
        df = self.df.copy()

        if df.empty:
            return df

        # Date filters
        if filters.start_date and 'date' in df.columns:
            df = df[df['date'] >= pd.to_datetime(filters.start_date)]

        if filters.end_date and 'date' in df.columns:
            df = df[df['date'] <= pd.to_datetime(filters.end_date)]

        # Amount filters
        if filters.min_amount is not None and 'amount' in df.columns:
            df = df[df['amount'] >= filters.min_amount]

        if filters.max_amount is not None and 'amount' in df.columns:
            df = df[df['amount'] <= filters.max_amount]

        # Category filters
        if filters.categories and 'category' in df.columns:
            df = df[df['category'].str.lower().isin([c.lower() for c in filters.categories])]

        if filters.exclude_categories and 'category' in df.columns:
            df = df[~df['category'].str.lower().isin([c.lower() for c in filters.exclude_categories])]

        # Merchant/Payee filters
        if filters.merchants and 'merchant' in df.columns:
            pattern = '|'.join(filters.merchants)
            df = df[df['merchant'].str.contains(pattern, case=False, na=False)]

        if filters.exclude_merchants and 'merchant' in df.columns:
            pattern = '|'.join(filters.exclude_merchants)
            df = df[~df['merchant'].str.contains(pattern, case=False, na=False)]

        # Account filters
        if filters.accounts and 'account' in df.columns:
            df = df[df['account'].str.lower().isin([a.lower() for a in filters.accounts])]

        # Description filters
        if filters.description_contains and 'description' in df.columns:
            df = df[df['description'].str.contains(
                filters.description_contains, case=False, na=False
            )]

        # Notes filters
        if filters.notes_contains and 'notes' in df.columns:
            df = df[df['notes'].str.contains(
                filters.notes_contains, case=False, na=False
            )]

        return df

    def apply_sort(self, df: pd.DataFrame, sort: ReportSort) -> pd.DataFrame:
        """
        Apply sorting to DataFrame

        Args:
            df: DataFrame to sort
            sort: ReportSort object with sort criteria

        Returns:
            Sorted DataFrame
        """
        if df.empty or sort.field not in df.columns:
            return df

        ascending = (sort.order == SortOrder.ASC)
        return df.sort_values(by=sort.field, ascending=ascending)

    def format_currency(self, amount: float) -> str:
        """Format amount as currency"""
        return f"${amount:,.2f}"

    def to_dict(self) -> Dict:
        """Convert report to dictionary (to be implemented by subclasses)"""
        raise NotImplementedError

    def to_json(self) -> str:
        """Convert report to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_csv(self, filename: str):
        """Export report data to CSV"""
        if not self.df.empty:
            self.df.to_csv(filename, index=False)


class ProfitAndLossReport(BaseReport):
    """
    Profit & Loss (Income Statement) Report

    Shows:
    - Total Income
    - Total Expenses by category
    - Net Income (Profit/Loss)
    - Income/Expense breakdown
    """

    def __init__(self, transactions: List[Dict], filters: Optional[ReportFilter] = None):
        super().__init__(transactions)
        self.filters = filters or ReportFilter()
        self.data = self._generate_report()

    def _generate_report(self) -> Dict:
        """Generate P&L report data"""
        df = self.apply_filters(self.filters)

        if df.empty:
            return {
                'report_type': 'Profit & Loss',
                'period': self._get_period_description(),
                'total_income': 0.0,
                'total_expenses': 0.0,
                'net_income': 0.0,
                'income_by_category': [],
                'expenses_by_category': [],
                'transaction_count': 0
            }

        # Separate income (positive amounts) and expenses (negative amounts)
        income_df = df[df['amount'] > 0].copy()
        expense_df = df[df['amount'] < 0].copy()

        # Calculate totals
        total_income = income_df['amount'].sum() if not income_df.empty else 0.0
        total_expenses = abs(expense_df['amount'].sum()) if not expense_df.empty else 0.0
        net_income = total_income - total_expenses

        # Income by category
        income_by_category = []
        if not income_df.empty and 'category' in income_df.columns:
            income_summary = income_df.groupby('category').agg({
                'amount': ['sum', 'count', 'mean']
            }).reset_index()
            income_summary.columns = ['category', 'total', 'count', 'average']

            for _, row in income_summary.iterrows():
                income_by_category.append({
                    'category': row['category'],
                    'total': float(row['total']),
                    'count': int(row['count']),
                    'average': float(row['average']),
                    'percentage_of_income': (float(row['total']) / total_income * 100) if total_income > 0 else 0
                })

            # Sort by total descending
            income_by_category.sort(key=lambda x: x['total'], reverse=True)

        # Expenses by category
        expenses_by_category = []
        if not expense_df.empty and 'category' in expense_df.columns:
            expense_summary = expense_df.groupby('category').agg({
                'amount': ['sum', 'count', 'mean']
            }).reset_index()
            expense_summary.columns = ['category', 'total', 'count', 'average']

            for _, row in expense_summary.iterrows():
                expense_amount = abs(float(row['total']))
                expenses_by_category.append({
                    'category': row['category'],
                    'total': expense_amount,
                    'count': int(row['count']),
                    'average': abs(float(row['average'])),
                    'percentage_of_expenses': (expense_amount / total_expenses * 100) if total_expenses > 0 else 0
                })

            # Sort by total descending
            expenses_by_category.sort(key=lambda x: x['total'], reverse=True)

        return {
            'report_type': 'Profit & Loss',
            'period': self._get_period_description(),
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'income_by_category': income_by_category,
            'expenses_by_category': expenses_by_category,
            'transaction_count': len(df),
            'income_transaction_count': len(income_df),
            'expense_transaction_count': len(expense_df)
        }

    def _get_period_description(self) -> str:
        """Get human-readable period description"""
        if self.filters.start_date and self.filters.end_date:
            return f"{self.filters.start_date} to {self.filters.end_date}"
        elif self.filters.start_date:
            return f"From {self.filters.start_date}"
        elif self.filters.end_date:
            return f"Until {self.filters.end_date}"
        else:
            return "All time"

    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return self.data

    def print_summary(self):
        """Print formatted P&L summary to console"""
        print("\n" + "="*80)
        print(f"PROFIT & LOSS REPORT")
        print(f"Period: {self.data['period']}")
        print("="*80)

        print(f"\nINCOME:")
        print(f"  Total Income:    {self.format_currency(self.data['total_income'])}")
        print(f"  Transactions:    {self.data['income_transaction_count']}")

        if self.data['income_by_category']:
            print(f"\n  Income by Category:")
            for cat in self.data['income_by_category']:
                print(f"    {cat['category']:30} {self.format_currency(cat['total']):>15} ({cat['percentage_of_income']:.1f}%)")

        print(f"\nEXPENSES:")
        print(f"  Total Expenses:  {self.format_currency(self.data['total_expenses'])}")
        print(f"  Transactions:    {self.data['expense_transaction_count']}")

        if self.data['expenses_by_category']:
            print(f"\n  Expenses by Category:")
            for cat in self.data['expenses_by_category']:
                print(f"    {cat['category']:30} {self.format_currency(cat['total']):>15} ({cat['percentage_of_expenses']:.1f}%)")

        print("\n" + "-"*80)
        net_label = "NET INCOME" if self.data['net_income'] >= 0 else "NET LOSS"
        print(f"{net_label}:       {self.format_currency(abs(self.data['net_income']))}")
        print("="*80 + "\n")


class CashFlowReport(BaseReport):
    """
    Cash Flow Report

    Shows:
    - Cash inflows and outflows over time
    - Net cash flow by period
    - Running balance
    """

    def __init__(self,
                 transactions: List[Dict],
                 filters: Optional[ReportFilter] = None,
                 grouping: TimeGrouping = TimeGrouping.MONTHLY):
        super().__init__(transactions)
        self.filters = filters or ReportFilter()
        self.grouping = grouping
        self.data = self._generate_report()

    def _generate_report(self) -> Dict:
        """Generate cash flow report data"""
        df = self.apply_filters(self.filters)

        if df.empty or 'date' not in df.columns:
            return {
                'report_type': 'Cash Flow',
                'grouping': self.grouping.value,
                'period': '',
                'periods': [],
                'total_inflow': 0.0,
                'total_outflow': 0.0,
                'net_cash_flow': 0.0
            }

        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])

        # Add period column based on grouping
        if self.grouping == TimeGrouping.DAILY:
            df['period'] = df['date'].dt.strftime('%Y-%m-%d')
        elif self.grouping == TimeGrouping.WEEKLY:
            df['period'] = df['date'].dt.to_period('W').astype(str)
        elif self.grouping == TimeGrouping.MONTHLY:
            df['period'] = df['date'].dt.strftime('%Y-%m')
        elif self.grouping == TimeGrouping.QUARTERLY:
            df['period'] = df['date'].dt.to_period('Q').astype(str)
        elif self.grouping == TimeGrouping.YEARLY:
            df['period'] = df['date'].dt.strftime('%Y')

        # Calculate inflows and outflows per period
        periods = []
        running_balance = 0.0

        for period_name in sorted(df['period'].unique()):
            period_df = df[df['period'] == period_name]

            inflow = period_df[period_df['amount'] > 0]['amount'].sum()
            outflow = abs(period_df[period_df['amount'] < 0]['amount'].sum())
            net_flow = inflow - outflow
            running_balance += net_flow

            periods.append({
                'period': period_name,
                'inflow': float(inflow),
                'outflow': float(outflow),
                'net_flow': float(net_flow),
                'running_balance': float(running_balance),
                'transaction_count': len(period_df)
            })

        total_inflow = sum(p['inflow'] for p in periods)
        total_outflow = sum(p['outflow'] for p in periods)

        return {
            'report_type': 'Cash Flow',
            'grouping': self.grouping.value,
            'period': f"{periods[0]['period']} to {periods[-1]['period']}" if periods else '',
            'periods': periods,
            'total_inflow': total_inflow,
            'total_outflow': total_outflow,
            'net_cash_flow': total_inflow - total_outflow
        }

    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return self.data

    def print_summary(self):
        """Print formatted cash flow summary"""
        print("\n" + "="*100)
        print(f"CASH FLOW REPORT ({self.data['grouping'].upper()})")
        print(f"Period: {self.data['period']}")
        print("="*100)

        print(f"\n{'Period':<15} {'Inflow':>15} {'Outflow':>15} {'Net Flow':>15} {'Running Balance':>20}")
        print("-"*100)

        for period in self.data['periods']:
            print(f"{period['period']:<15} "
                  f"{self.format_currency(period['inflow']):>15} "
                  f"{self.format_currency(period['outflow']):>15} "
                  f"{self.format_currency(period['net_flow']):>15} "
                  f"{self.format_currency(period['running_balance']):>20}")

        print("-"*100)
        print(f"{'TOTAL':<15} "
              f"{self.format_currency(self.data['total_inflow']):>15} "
              f"{self.format_currency(self.data['total_outflow']):>15} "
              f"{self.format_currency(self.data['net_cash_flow']):>15}")
        print("="*100 + "\n")


class CategoryAnalysisReport(BaseReport):
    """
    Category Analysis Report

    Detailed breakdown of transactions by category with statistics
    """

    def __init__(self,
                 transactions: List[Dict],
                 filters: Optional[ReportFilter] = None,
                 top_n: Optional[int] = None):
        super().__init__(transactions)
        self.filters = filters or ReportFilter()
        self.top_n = top_n
        self.data = self._generate_report()

    def _generate_report(self) -> Dict:
        """Generate category analysis report"""
        df = self.apply_filters(self.filters)

        if df.empty or 'category' not in df.columns:
            return {
                'report_type': 'Category Analysis',
                'categories': [],
                'total_amount': 0.0,
                'category_count': 0
            }

        # Group by category
        category_summary = df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean', 'min', 'max', 'std']
        }).reset_index()
        category_summary.columns = ['category', 'total', 'count', 'average', 'min', 'max', 'std']

        # Sort by total amount
        category_summary = category_summary.sort_values('total', ascending=False)

        # Apply top_n limit if specified
        if self.top_n:
            category_summary = category_summary.head(self.top_n)

        total_amount = df['amount'].sum()

        categories = []
        for _, row in category_summary.iterrows():
            cat_total = float(row['total'])
            categories.append({
                'category': row['category'],
                'total': cat_total,
                'count': int(row['count']),
                'average': float(row['average']),
                'min': float(row['min']),
                'max': float(row['max']),
                'std_dev': float(row['std']) if pd.notna(row['std']) else 0.0,
                'percentage_of_total': (abs(cat_total) / abs(total_amount) * 100) if total_amount != 0 else 0
            })

        return {
            'report_type': 'Category Analysis',
            'categories': categories,
            'total_amount': float(total_amount),
            'category_count': len(categories)
        }

    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return self.data

    def print_summary(self):
        """Print formatted category analysis"""
        print("\n" + "="*120)
        print(f"CATEGORY ANALYSIS REPORT")
        if self.top_n:
            print(f"Top {self.top_n} Categories")
        print("="*120)

        print(f"\n{'Category':<25} {'Total':>15} {'Count':>8} {'Average':>15} {'Min':>15} {'Max':>15} {'%':>8}")
        print("-"*120)

        for cat in self.data['categories']:
            print(f"{cat['category']:<25} "
                  f"{self.format_currency(cat['total']):>15} "
                  f"{cat['count']:>8} "
                  f"{self.format_currency(cat['average']):>15} "
                  f"{self.format_currency(cat['min']):>15} "
                  f"{self.format_currency(cat['max']):>15} "
                  f"{cat['percentage_of_total']:>7.1f}%")

        print("-"*120)
        print(f"{'TOTAL':<25} {self.format_currency(self.data['total_amount']):>15} "
              f"({self.data['category_count']} categories)")
        print("="*120 + "\n")


class MerchantAnalysisReport(BaseReport):
    """
    Merchant/Payee Analysis Report

    Breakdown of spending by merchant/payee
    """

    def __init__(self,
                 transactions: List[Dict],
                 filters: Optional[ReportFilter] = None,
                 top_n: int = 20):
        super().__init__(transactions)
        self.filters = filters or ReportFilter()
        self.top_n = top_n
        self.data = self._generate_report()

    def _generate_report(self) -> Dict:
        """Generate merchant analysis report"""
        df = self.apply_filters(self.filters)

        if df.empty or 'merchant' not in df.columns:
            return {
                'report_type': 'Merchant Analysis',
                'merchants': [],
                'total_amount': 0.0,
                'merchant_count': 0
            }

        # Group by merchant
        merchant_summary = df.groupby('merchant').agg({
            'amount': ['sum', 'count', 'mean'],
            'category': lambda x: x.mode()[0] if len(x.mode()) > 0 else ''
        }).reset_index()
        merchant_summary.columns = ['merchant', 'total', 'count', 'average', 'primary_category']

        # Sort by absolute total amount (to catch both expenses and income)
        merchant_summary['abs_total'] = merchant_summary['total'].abs()
        merchant_summary = merchant_summary.sort_values('abs_total', ascending=False)

        # Apply top_n limit
        merchant_summary = merchant_summary.head(self.top_n)

        total_amount = df['amount'].sum()

        merchants = []
        for _, row in merchant_summary.iterrows():
            merch_total = float(row['total'])
            merchants.append({
                'merchant': row['merchant'],
                'total': merch_total,
                'count': int(row['count']),
                'average': float(row['average']),
                'primary_category': row['primary_category'],
                'percentage_of_total': (abs(merch_total) / abs(total_amount) * 100) if total_amount != 0 else 0
            })

        return {
            'report_type': 'Merchant Analysis',
            'merchants': merchants,
            'total_amount': float(total_amount),
            'merchant_count': len(merchants)
        }

    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return self.data

    def print_summary(self):
        """Print formatted merchant analysis"""
        print("\n" + "="*110)
        print(f"MERCHANT/PAYEE ANALYSIS REPORT (Top {self.top_n})")
        print("="*110)

        print(f"\n{'Merchant':<30} {'Total':>15} {'Count':>8} {'Average':>15} {'Category':<20} {'%':>8}")
        print("-"*110)

        for merch in self.data['merchants']:
            print(f"{merch['merchant'][:30]:<30} "
                  f"{self.format_currency(merch['total']):>15} "
                  f"{merch['count']:>8} "
                  f"{self.format_currency(merch['average']):>15} "
                  f"{merch['primary_category'][:20]:<20} "
                  f"{merch['percentage_of_total']:>7.1f}%")

        print("="*110 + "\n")


class TrendAnalysisReport(BaseReport):
    """
    Trend Analysis Report

    Shows trends over time for income, expenses, and categories
    """

    def __init__(self,
                 transactions: List[Dict],
                 filters: Optional[ReportFilter] = None,
                 grouping: TimeGrouping = TimeGrouping.MONTHLY):
        super().__init__(transactions)
        self.filters = filters or ReportFilter()
        self.grouping = grouping
        self.data = self._generate_report()

    def _generate_report(self) -> Dict:
        """Generate trend analysis report"""
        df = self.apply_filters(self.filters)

        if df.empty or 'date' not in df.columns:
            return {
                'report_type': 'Trend Analysis',
                'grouping': self.grouping.value,
                'periods': []
            }

        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])

        # Add period column
        if self.grouping == TimeGrouping.DAILY:
            df['period'] = df['date'].dt.strftime('%Y-%m-%d')
        elif self.grouping == TimeGrouping.WEEKLY:
            df['period'] = df['date'].dt.to_period('W').astype(str)
        elif self.grouping == TimeGrouping.MONTHLY:
            df['period'] = df['date'].dt.strftime('%Y-%m')
        elif self.grouping == TimeGrouping.QUARTERLY:
            df['period'] = df['date'].dt.to_period('Q').astype(str)
        elif self.grouping == TimeGrouping.YEARLY:
            df['period'] = df['date'].dt.strftime('%Y')

        periods = []

        for period_name in sorted(df['period'].unique()):
            period_df = df[df['period'] == period_name]

            income = period_df[period_df['amount'] > 0]['amount'].sum()
            expenses = abs(period_df[period_df['amount'] < 0]['amount'].sum())
            net = income - expenses

            # Top category for period
            if 'category' in period_df.columns:
                top_expense_cat = None
                if len(period_df[period_df['amount'] < 0]) > 0:
                    cat_totals = period_df[period_df['amount'] < 0].groupby('category')['amount'].sum()
                    if len(cat_totals) > 0:
                        top_expense_cat = cat_totals.idxmin()  # Most negative = highest expense
            else:
                top_expense_cat = None

            periods.append({
                'period': period_name,
                'income': float(income),
                'expenses': float(expenses),
                'net': float(net),
                'transaction_count': len(period_df),
                'top_expense_category': top_expense_cat
            })

        return {
            'report_type': 'Trend Analysis',
            'grouping': self.grouping.value,
            'periods': periods
        }

    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return self.data

    def print_summary(self):
        """Print formatted trend analysis"""
        print("\n" + "="*110)
        print(f"TREND ANALYSIS REPORT ({self.data['grouping'].upper()})")
        print("="*110)

        print(f"\n{'Period':<15} {'Income':>15} {'Expenses':>15} {'Net':>15} {'Txns':>8} {'Top Expense Category':<25}")
        print("-"*110)

        for period in self.data['periods']:
            top_cat = period['top_expense_category'] or 'N/A'
            print(f"{period['period']:<15} "
                  f"{self.format_currency(period['income']):>15} "
                  f"{self.format_currency(period['expenses']):>15} "
                  f"{self.format_currency(period['net']):>15} "
                  f"{period['transaction_count']:>8} "
                  f"{top_cat[:25]:<25}")

        print("="*110 + "\n")


class AccountSummaryReport(BaseReport):
    """
    Account Summary Report

    Breakdown by account with balances and activity
    """

    def __init__(self, transactions: List[Dict], filters: Optional[ReportFilter] = None):
        super().__init__(transactions)
        self.filters = filters or ReportFilter()
        self.data = self._generate_report()

    def _generate_report(self) -> Dict:
        """Generate account summary report"""
        df = self.apply_filters(self.filters)

        if df.empty or 'account' not in df.columns:
            return {
                'report_type': 'Account Summary',
                'accounts': [],
                'total_balance_change': 0.0
            }

        accounts = []

        for account_name in sorted(df['account'].unique()):
            account_df = df[df['account'] == account_name]

            income = account_df[account_df['amount'] > 0]['amount'].sum()
            expenses = abs(account_df[account_df['amount'] < 0]['amount'].sum())
            balance_change = income - expenses

            accounts.append({
                'account': account_name,
                'income': float(income),
                'expenses': float(expenses),
                'balance_change': float(balance_change),
                'transaction_count': len(account_df)
            })

        # Sort by absolute balance change
        accounts.sort(key=lambda x: abs(x['balance_change']), reverse=True)

        total_balance_change = sum(a['balance_change'] for a in accounts)

        return {
            'report_type': 'Account Summary',
            'accounts': accounts,
            'total_balance_change': total_balance_change
        }

    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return self.data

    def print_summary(self):
        """Print formatted account summary"""
        print("\n" + "="*100)
        print(f"ACCOUNT SUMMARY REPORT")
        print("="*100)

        print(f"\n{'Account':<30} {'Income':>15} {'Expenses':>15} {'Net Change':>15} {'Txns':>8}")
        print("-"*100)

        for account in self.data['accounts']:
            print(f"{account['account'][:30]:<30} "
                  f"{self.format_currency(account['income']):>15} "
                  f"{self.format_currency(account['expenses']):>15} "
                  f"{self.format_currency(account['balance_change']):>15} "
                  f"{account['transaction_count']:>8}")

        print("-"*100)
        print(f"{'TOTAL':<30} {'':>15} {'':>15} "
              f"{self.format_currency(self.data['total_balance_change']):>15}")
        print("="*100 + "\n")


class ReportBuilder:
    """
    Main Report Builder class

    Provides a unified interface for building various financial reports
    """

    def __init__(self, transactions: List[Dict]):
        """
        Initialize report builder with transactions

        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = transactions

    def profit_and_loss(self, filters: Optional[ReportFilter] = None) -> ProfitAndLossReport:
        """
        Generate Profit & Loss report

        Args:
            filters: Optional filters to apply

        Returns:
            ProfitAndLossReport instance
        """
        return ProfitAndLossReport(self.transactions, filters)

    def cash_flow(self,
                  filters: Optional[ReportFilter] = None,
                  grouping: TimeGrouping = TimeGrouping.MONTHLY) -> CashFlowReport:
        """
        Generate Cash Flow report

        Args:
            filters: Optional filters to apply
            grouping: Time grouping (daily, weekly, monthly, etc.)

        Returns:
            CashFlowReport instance
        """
        return CashFlowReport(self.transactions, filters, grouping)

    def category_analysis(self,
                         filters: Optional[ReportFilter] = None,
                         top_n: Optional[int] = None) -> CategoryAnalysisReport:
        """
        Generate Category Analysis report

        Args:
            filters: Optional filters to apply
            top_n: Limit to top N categories

        Returns:
            CategoryAnalysisReport instance
        """
        return CategoryAnalysisReport(self.transactions, filters, top_n)

    def merchant_analysis(self,
                         filters: Optional[ReportFilter] = None,
                         top_n: int = 20) -> MerchantAnalysisReport:
        """
        Generate Merchant Analysis report

        Args:
            filters: Optional filters to apply
            top_n: Number of top merchants to show

        Returns:
            MerchantAnalysisReport instance
        """
        return MerchantAnalysisReport(self.transactions, filters, top_n)

    def trend_analysis(self,
                      filters: Optional[ReportFilter] = None,
                      grouping: TimeGrouping = TimeGrouping.MONTHLY) -> TrendAnalysisReport:
        """
        Generate Trend Analysis report

        Args:
            filters: Optional filters to apply
            grouping: Time grouping (daily, weekly, monthly, etc.)

        Returns:
            TrendAnalysisReport instance
        """
        return TrendAnalysisReport(self.transactions, filters, grouping)

    def account_summary(self, filters: Optional[ReportFilter] = None) -> AccountSummaryReport:
        """
        Generate Account Summary report

        Args:
            filters: Optional filters to apply

        Returns:
            AccountSummaryReport instance
        """
        return AccountSummaryReport(self.transactions, filters)

    def custom_report(self,
                     filters: Optional[ReportFilter] = None,
                     sort: Optional[ReportSort] = None,
                     group_by: Optional[str] = None) -> Dict:
        """
        Generate custom report with flexible filtering and sorting

        Args:
            filters: Filters to apply
            sort: Sort configuration
            group_by: Field to group by (category, merchant, account, etc.)

        Returns:
            Dictionary with report data
        """
        base_report = BaseReport(self.transactions)
        df = base_report.apply_filters(filters or ReportFilter())

        if sort:
            df = base_report.apply_sort(df, sort)

        if group_by and group_by in df.columns:
            grouped = df.groupby(group_by).agg({
                'amount': ['sum', 'count', 'mean', 'min', 'max']
            }).reset_index()
            grouped.columns = [group_by, 'total', 'count', 'average', 'min', 'max']

            return {
                'report_type': 'Custom Report',
                'grouped_by': group_by,
                'data': grouped.to_dict('records'),
                'total_amount': float(df['amount'].sum()),
                'transaction_count': len(df)
            }
        else:
            return {
                'report_type': 'Custom Report',
                'transactions': df.to_dict('records'),
                'total_amount': float(df['amount'].sum()),
                'transaction_count': len(df)
            }
