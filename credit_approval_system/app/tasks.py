import pandas as pd
from .models import Customer, Loan
from celery import shared_task

@shared_task
def ingest_customer_data(file_path='data/customer_data.xlsx'):
    data = pd.read_excel(file_path, engine='openpyxl')
    print(data.head())  # Debug: Print the first few rows to confirm data is read correctly
    for _, row in data.iterrows():
        Customer.objects.create(
            first_name=row['First Name'],
            last_name=row['Last Name'],
            phone_number=row['Phone Number'],
            monthly_salary=row['Monthly Salary'],
            approved_limit=round(row['Monthly Salary'] * 36, -5),
            current_debt=0
        )

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
            emis_paid_on_time=row['EMIs paid on Time'],  # Ensure a valid value
            start_date=row['Date of Approval'] if pd.notnull(row['Date of Approval']) else None,
            end_date=row['End Date'] if pd.notnull(row['End Date']) else None
        )

