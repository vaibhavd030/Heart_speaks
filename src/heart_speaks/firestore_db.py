"""
Firestore client singleton for heart_speaks.

Uses Application Default Credentials (ADC) which work automatically
on Cloud Run. For local development, run:
    gcloud auth application-default login
"""

from google.cloud import firestore

_client: firestore.Client | None = None


def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client."""
    global _client
    if _client is None:
        _client = firestore.Client(project="my-tele-pa", database="(default)")
    return _client
