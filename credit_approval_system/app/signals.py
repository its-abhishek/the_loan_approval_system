from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .tasks import ingest_customer_data, ingest_loan_data

@receiver(post_migrate)
def auto_ingest_data(sender, **kwargs):
    if sender.name == 'app':
        print("Starting data ingestion...")
        ingest_customer_data('data/customer_data.xlsx')
        ingest_loan_data('data/loan_data.xlsx')