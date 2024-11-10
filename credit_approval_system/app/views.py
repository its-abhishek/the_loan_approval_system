from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import models
from datetime import date
from dateutil.relativedelta import relativedelta
from .models import Customer, Loan

@api_view(['POST'])
def register_customer(request):
    data = request.data

    # Validate unique phone number
    if Customer.objects.filter(phone_number=data['phone_number']).exists():
        return Response(
            {"error": "A customer with this phone number already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create new customer
    customer = Customer(
        first_name=data['first_name'],
        last_name=data['last_name'],
        age=data['age'],
        phone_number=data['phone_number'],
        monthly_salary=data['monthly_income'],
        approved_limit=round(data['monthly_income'] * 36, -5)
    )
    customer.save()

    response_data = {
        "customer_id": customer.customer_id,
        "name": f"{customer.first_name} {customer.last_name}",
        "age": customer.age,
        "monthly_income": customer.monthly_salary,
        "approved_limit": customer.approved_limit,
        "phone_number": customer.phone_number
    }

    return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def check_eligibility(request):
    data = request.data
    try:
        customer = Customer.objects.get(customer_id=data['customer_id'])
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    loans = Loan.objects.filter(customer=customer)
    total_loan_amount = sum(loan.loan_amount for loan in loans)

    # Check if current loans exceed approved limit
    if total_loan_amount + data['loan_amount'] > customer.approved_limit:
        return Response({
            "customer_id": customer.customer_id,
            "credit_score": 0,
            "approval": False,
            "message": "Current loans exceed approved limit",
            "interest_rate": data['interest_rate'],
            "corrected_interest_rate": data['interest_rate'],
            "tenure": data['tenure'],
            "monthly_installment": 0
        }, status=status.HTTP_400_BAD_REQUEST)

    # Calculate credit score
    credit_score = 0
    past_loans_paid_on_time = loans.filter(emis_paid_on_time=True).count()
    number_of_loans = loans.count()
    current_year_loans = loans.filter(start_date__year=date.today().year).count()
    loan_volume = total_loan_amount

    # Assign credit score based on criteria
    credit_score += past_loans_paid_on_time * 10  # Example: 10 points for each on-time loan
    credit_score += number_of_loans * 5           # Example: 5 points for each loan taken
    credit_score += current_year_loans * 5        # Example: 5 points for loans in the current year
    credit_score += min(loan_volume / 10000, 20)  # Example: max 20 points for loan volume

    # Check if sum of EMIs exceeds 50% of monthly salary
    total_emis = sum(loan.monthly_repayment for loan in loans)
    if total_emis + data['loan_amount'] * (1 + data['interest_rate'] / 100) / data['tenure'] > 0.5 * customer.monthly_salary:
        return Response({
            "customer_id": customer.customer_id,
            "credit_score": credit_score,
            "approval": False,
            "message": "EMIs exceed 50% of monthly salary",
            "interest_rate": data['interest_rate'],
            "corrected_interest_rate": data['interest_rate'],
            "tenure": data['tenure'],
            "monthly_installment": 0
        }, status=status.HTTP_400_BAD_REQUEST)

    # Determine loan approval based on credit score
    approval = False
    corrected_interest_rate = data['interest_rate']

    if credit_score > 50:
        approval = True
    elif 30 < credit_score <= 50:
        approval = True if data['interest_rate'] >= 12 else False
    elif 10 < credit_score <= 30:
        approval = True if data['interest_rate'] >= 16 else False
    else:
        approval = False

    # Correct interest rate if needed
    if credit_score <= 50 and approval:
        if 30 < credit_score <= 50 and data['interest_rate'] < 12:
            corrected_interest_rate = 12
        elif 10 < credit_score <= 30 and data['interest_rate'] < 16:
            corrected_interest_rate = 16

    response_data = {
        "customer_id": customer.customer_id,
        "credit_score": credit_score,
        "approval": approval,
        "message": "Loan approved" if approval else "Loan not approved based on credit score",
        "interest_rate": data['interest_rate'],
        "corrected_interest_rate": corrected_interest_rate,
        "tenure": data['tenure'],
        "monthly_installment": 0
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
def create_loan(request):
    data = request.data
    print("Received request data:", data)  # Debug: Print incoming request data

    try:
        customer = Customer.objects.get(customer_id=data['customer_id'])
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    # Fetch all loans for the customer to calculate credit score
    loans = Loan.objects.filter(customer=customer)

    # Calculate credit score
    credit_score = 0
    past_loans_paid_on_time = loans.filter(emis_paid_on_time=True).count()
    number_of_loans = loans.count()
    current_year_loans = loans.filter(start_date__year=date.today().year).count()
    loan_volume = sum(loan.loan_amount for loan in loans)

    credit_score += past_loans_paid_on_time * 10
    credit_score += number_of_loans * 5
    credit_score += current_year_loans * 5
    credit_score += min(loan_volume / 10000, 20)

    # Check if total EMIs exceed 50% of monthly salary
    total_emis = sum(loan.monthly_repayment for loan in loans)
    if total_emis + (data['loan_amount'] * (1 + data['interest_rate'] / 100) / data['tenure']) > 0.5 * customer.monthly_salary:
        return Response({
            "loan_approved": False,
            "message": "EMIs exceed 50% of monthly salary",
            "monthly_installment": 0
        }, status=status.HTTP_400_BAD_REQUEST)

    # Loan Approval Logic
    approval = False
    if credit_score > 50:
        approval = True
    elif 30 < credit_score <= 50 and data['interest_rate'] >= 12:
        approval = True
    elif 10 < credit_score <= 30 and data['interest_rate'] >= 16:
        approval = True

    if not approval:
        return Response({
            "loan_approved": False,
            "message": "Loan not approved based on credit score",
            "monthly_installment": 0
        }, status=status.HTTP_400_BAD_REQUEST)

    # Calculate EMI
    monthly_installment = (data['loan_amount'] * (1 + (data['interest_rate'] / 100) * (data['tenure'] / 12))) / data['tenure']

    # Create the loan record
    start_date = date.today()
    end_date = start_date + relativedelta(months=data['tenure'])

    loan = Loan.objects.create(
        customer=customer,
        loan_amount=data['loan_amount'],
        tenure=data['tenure'],
        interest_rate=data['interest_rate'],
        monthly_repayment=monthly_installment,
        emis_paid_on_time=False,  # Assuming default value
        start_date=start_date,
        end_date=end_date
    )

    return Response({
        "loan_id": loan.loan_id,
        "customer_id": customer.customer_id,
        "loan_approved": True,
        "message": "Loan approved",
        "monthly_installment": monthly_installment,
        "start_date": start_date,
        "end_date": end_date
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def view_loan(request, loan_id):
    try:
        loan = Loan.objects.get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response({"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND)

    customer_data = {
        "id": loan.customer.customer_id,
        "first_name": loan.customer.first_name,
        "last_name": loan.customer.last_name,
        "phone_number": loan.customer.phone_number,
        "age": loan.customer.age
    }

    response_data = {
        "loan_id": loan.loan_id,
        "customer": customer_data,
        "loan_amount": loan.loan_amount,
        "interest_rate": loan.interest_rate,
        "monthly_installment": loan.monthly_repayment,
        "tenure": loan.tenure
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['GET'])
def view_loans_by_customer(request, customer_id):
    loans = Loan.objects.filter(customer_id=customer_id)
    if not loans.exists():
        return Response({"error": "No loans found for this customer"}, status=status.HTTP_404_NOT_FOUND)

    response_data = []
    for loan in loans:
        response_data.append({
            "loan_id": loan.loan_id,
            "loan_amount": loan.loan_amount,
            "interest_rate": loan.interest_rate,
            "monthly_installment": loan.monthly_repayment,
            "repayments_left": loan.tenure
        })

    return Response(response_data, status=status.HTTP_200_OK)

