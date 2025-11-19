"""
Example usage of the Financial Report Builder

This script demonstrates how to use the report builder to generate
various financial reports from Simplifi transaction data.

Usage:
    python example_reports.py

Author: Financial Report Builder
Date: 2025-11-19
"""

import os
from dotenv import load_dotenv
from simplifi_client import SimplifiClient
from transaction_downloader import TransactionDownloader
from report_builder import (
    ReportBuilder,
    ReportFilter,
    ReportSort,
    SortOrder,
    TimeGrouping
)


def example_profit_and_loss():
    """Example: Generate a Profit & Loss report for the last 90 days"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Profit & Loss Report (Last 90 Days)")
    print("="*80)

    # Load environment variables
    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        # Download last 90 days of transactions
        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=90)

        if not transactions:
            print("No transactions found")
            return

        # Create report builder
        builder = ReportBuilder(transactions)

        # Generate P&L report for last 90 days
        filters = ReportFilter(
            # Date filtering already done by download_transactions
        )

        report = builder.profit_and_loss(filters)

        # Print the report
        report.print_summary()

        # Export to JSON
        with open('reports/profit_and_loss_90days.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/profit_and_loss_90days.json")


def example_monthly_cash_flow():
    """Example: Generate monthly cash flow report for current year"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Monthly Cash Flow Report (Current Year)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)

        # Download current year transactions
        filters = ReportFilter(
            start_date="2025-01-01",
            end_date="2025-12-31"
        )

        transactions = downloader.download_transactions(
            start_date=filters.start_date,
            end_date=filters.end_date
        )

        if not transactions:
            print("No transactions found")
            return

        # Create cash flow report grouped by month
        builder = ReportBuilder(transactions)
        report = builder.cash_flow(filters, grouping=TimeGrouping.MONTHLY)

        report.print_summary()

        # Save to JSON
        with open('reports/cash_flow_monthly_2025.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/cash_flow_monthly_2025.json")


def example_category_analysis_expenses():
    """Example: Analyze top expense categories for last 30 days"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Top 10 Expense Categories (Last 30 Days)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=30)

        if not transactions:
            print("No transactions found")
            return

        # Filter for expenses only (negative amounts)
        builder = ReportBuilder(transactions)

        filters = ReportFilter(
            max_amount=-0.01  # Only negative amounts (expenses)
        )

        report = builder.category_analysis(filters, top_n=10)
        report.print_summary()

        # Save to JSON
        with open('reports/top_expense_categories_30days.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/top_expense_categories_30days.json")


def example_merchant_analysis():
    """Example: Top merchants/payees for last quarter"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Top 20 Merchants (Last Quarter)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=90)

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        # Analyze top 20 merchants
        report = builder.merchant_analysis(top_n=20)
        report.print_summary()

        # Save to JSON
        with open('reports/top_merchants_quarter.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/top_merchants_quarter.json")


def example_filtered_p_and_l():
    """Example: P&L for specific categories only"""
    print("\n" + "="*80)
    print("EXAMPLE 5: P&L for Food & Dining Categories (Last 60 Days)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=60)

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        # Filter for food-related categories
        filters = ReportFilter(
            categories=[
                'Restaurants & Dining',
                'Groceries',
                'Coffee Shops',
                'Fast Food',
                'Food & Drink'
            ]
        )

        report = builder.profit_and_loss(filters)
        report.print_summary()

        # Save to JSON
        with open('reports/food_dining_p_and_l_60days.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/food_dining_p_and_l_60days.json")


def example_trend_analysis():
    """Example: Monthly trend analysis for the year"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Monthly Trend Analysis (Last 12 Months)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=365)

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        # Generate monthly trends
        report = builder.trend_analysis(grouping=TimeGrouping.MONTHLY)
        report.print_summary()

        # Save to JSON
        with open('reports/monthly_trends_12months.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/monthly_trends_12months.json")


def example_account_summary():
    """Example: Summary by account"""
    print("\n" + "="*80)
    print("EXAMPLE 7: Account Summary (Last 90 Days)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=90)

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        # Generate account summary
        report = builder.account_summary()
        report.print_summary()

        # Save to JSON
        with open('reports/account_summary_90days.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/account_summary_90days.json")


def example_custom_report_with_filters():
    """Example: Custom report with complex filters"""
    print("\n" + "="*80)
    print("EXAMPLE 8: Custom Report - Large Transactions with Notes")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=90)

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        # Complex filters
        filters = ReportFilter(
            min_amount=100,  # Transactions over $100
            exclude_categories=['Transfer', 'Payment'],  # Exclude transfers
            notes_contains=""  # Has notes (non-empty)
        )

        sort = ReportSort(field='amount', order=SortOrder.DESC)

        report = builder.custom_report(
            filters=filters,
            sort=sort,
            group_by='category'
        )

        print(f"\nCustom Report Results:")
        print(f"Total Amount: ${report['total_amount']:,.2f}")
        print(f"Transaction Count: {report['transaction_count']}")

        if 'data' in report:
            print(f"\nGrouped by {report['grouped_by']}:")
            for item in report['data'][:10]:  # Show top 10
                print(f"  {item[report['grouped_by']]}: ${item['total']:,.2f} ({item['count']} txns)")

        # Save to JSON
        import json
        with open('reports/custom_large_with_notes.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print("\nReport saved to: reports/custom_large_with_notes.json")


def example_quarterly_comparison():
    """Example: Compare quarterly P&L"""
    print("\n" + "="*80)
    print("EXAMPLE 9: Quarterly P&L Comparison")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)

        # Download full year
        transactions = downloader.download_transactions(
            start_date="2025-01-01",
            end_date="2025-12-31"
        )

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        quarters = [
            ("Q1 2025", "2025-01-01", "2025-03-31"),
            ("Q2 2025", "2025-04-01", "2025-06-30"),
            ("Q3 2025", "2025-07-01", "2025-09-30"),
            ("Q4 2025", "2025-10-01", "2025-12-31"),
        ]

        results = []

        for quarter_name, start_date, end_date in quarters:
            filters = ReportFilter(
                start_date=start_date,
                end_date=end_date
            )

            report = builder.profit_and_loss(filters)
            data = report.to_dict()

            results.append({
                'quarter': quarter_name,
                'income': data['total_income'],
                'expenses': data['total_expenses'],
                'net_income': data['net_income']
            })

        # Print comparison
        print(f"\n{'Quarter':<15} {'Income':>15} {'Expenses':>15} {'Net Income':>15}")
        print("-" * 65)

        for result in results:
            print(f"{result['quarter']:<15} "
                  f"${result['income']:>14,.2f} "
                  f"${result['expenses']:>14,.2f} "
                  f"${result['net_income']:>14,.2f}")

        # Save comparison
        import json
        with open('reports/quarterly_comparison_2025.json', 'w') as f:
            json.dump(results, f, indent=2)

        print("\nComparison saved to: reports/quarterly_comparison_2025.json")


def example_exclude_transfers():
    """Example: P&L excluding transfers and internal movements"""
    print("\n" + "="*80)
    print("EXAMPLE 10: P&L Excluding Transfers (Last 30 Days)")
    print("="*80)

    load_dotenv()

    with SimplifiClient(headless=True) as client:
        if not client.login():
            print("Failed to login")
            return

        downloader = TransactionDownloader(client)
        transactions = downloader.download_transactions(days=30)

        if not transactions:
            print("No transactions found")
            return

        builder = ReportBuilder(transactions)

        # Exclude common transfer-related categories
        filters = ReportFilter(
            exclude_categories=[
                'Transfer',
                'Credit Card Payment',
                'Internal Transfer',
                'Savings Transfer',
                'Investment Transfer'
            ]
        )

        report = builder.profit_and_loss(filters)
        report.print_summary()

        # Save to JSON
        with open('reports/p_and_l_no_transfers_30days.json', 'w') as f:
            f.write(report.to_json())

        print("Report saved to: reports/p_and_l_no_transfers_30days.json")


def run_all_examples():
    """Run all examples (for demonstration)"""

    # Create reports directory if it doesn't exist
    os.makedirs('reports', exist_ok=True)

    examples = [
        ("Profit & Loss", example_profit_and_loss),
        ("Monthly Cash Flow", example_monthly_cash_flow),
        ("Top Expense Categories", example_category_analysis_expenses),
        ("Top Merchants", example_merchant_analysis),
        ("Filtered P&L", example_filtered_p_and_l),
        ("Trend Analysis", example_trend_analysis),
        ("Account Summary", example_account_summary),
        ("Custom Report", example_custom_report_with_filters),
        ("Quarterly Comparison", example_quarterly_comparison),
        ("P&L Excluding Transfers", example_exclude_transfers),
    ]

    print("\n" + "="*80)
    print("FINANCIAL REPORT BUILDER - EXAMPLES")
    print("="*80)
    print("\nAvailable examples:")

    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\n" + "="*80)

    choice = input("\nEnter example number to run (or 'all' to run all): ").strip()

    if choice.lower() == 'all':
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"Error running {name}: {e}")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        name, func = examples[int(choice) - 1]
        try:
            func()
        except Exception as e:
            print(f"Error running {name}: {e}")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    # Check if .env exists
    if not os.path.exists('.env'):
        print("ERROR: .env file not found!")
        print("Please create a .env file with your Simplifi credentials:")
        print("  SIMPLIFI_EMAIL=your_email@example.com")
        print("  SIMPLIFI_PASSWORD=your_password")
        exit(1)

    run_all_examples()
