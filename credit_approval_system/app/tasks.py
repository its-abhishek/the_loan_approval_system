import pandas as pd
from .models import Customer, Loan
from celery import shared_task
from datetime import date

@shared_task
def ingest_customer_data(file_path='data/customer_data.xlsx'):
    """Ingest customer data from an Excel file and estimate current debt."""
    data = pd.read_excel(file_path, engine='openpyxl')
    print(data.head())

    for _, row in data.iterrows():
        # Create customer record
        customer = Customer.objects.create(
            first_name=row['First Name'],
            last_name=row['Last Name'],
            age=row['Age'],
            phone_number=row['Phone Number'],
            monthly_salary=row['Monthly Salary'],
            approved_limit=row['Approved Limit'],
            current_debt=0  # Initialize as 0; will be updated with the estimation logic
        )
        
        # Example estimation of current debt as a percentage of approved limit
        estimated_debt_ratio = 0.3  # Assume 30% of approved limit as current debt for simplicity
        customer.current_debt = customer.approved_limit * estimated_debt_ratio
        
        # Save the updated current debt
        customer.save()

@shared_task
def ingest_loan_data(file_path='data/loan_data.xlsx'):
    data = pd.read_excel(file_path, engine='openpyxl')
    
    # Ensure 'EMIs paid on Time' is converted to boolean or defaults to False if missing
    data['EMIs paid on Time'] = data['EMIs paid on Time'].apply(
        lambda x: bool(x) if pd.notnull(x) else False
    )

    for _, row in data.iterrows():
        Loan.objects.create(
            customer_id=row['Customer ID'],
            loan_amount=row['Loan Amount'],
            tenure=row['Tenure'],
            interest_rate=row['Interest Rate'],
            monthly_repayment=row['Monthly payment'],
            emis_paid_on_time=row['EMIs paid on Time'],
            start_date=row['Date of Approval'] if pd.notnull(row['Date of Approval']) else None,
            end_date=row['End Date'] if pd.notnull(row['End Date']) else None
        )