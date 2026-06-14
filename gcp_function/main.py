import json
import os
from datetime import datetime, timezone

import functions_framework
import requests
from google.cloud import bigquery
from google.cloud import storage


@functions_framework.http
def ingest_transactions(request):
    """
    Cloud Function entry point.

    This function:
    1. Calls the external FastAPI transactions endpoint.
    2. Stores the raw API response in Cloud Storage.
    3. Inserts structured transaction rows into BigQuery.
    """

    external_api_url = os.environ.get("EXTERNAL_API_URL")
    api_key = os.environ.get("API_KEY")
    gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME")
    bq_dataset = os.environ.get("BQ_DATASET")
    bq_table = os.environ.get("BQ_TABLE")

    required_env_vars = {
        "EXTERNAL_API_URL": external_api_url,
        "API_KEY": api_key,
        "GCS_BUCKET_NAME": gcs_bucket_name,
        "BQ_DATASET": bq_dataset,
        "BQ_TABLE": bq_table,
    }

    missing_env_vars = [
        name for name, value in required_env_vars.items()
        if not value
    ]

    if missing_env_vars:
        return (
            json.dumps({
                "status": "error",
                "message": "Missing required environment variables.",
                "missing_env_vars": missing_env_vars
            }),
            500,
            {"Content-Type": "application/json"},
        )

    run_timestamp = datetime.now(timezone.utc)
    ingestion_timestamp = run_timestamp.isoformat()

    transactions_endpoint = f"{external_api_url.rstrip('/')}/transactions"

    headers = {
        "x-api-key": api_key,
        "ngrok-skip-browser-warning": "true"
    }

    try:
        response = requests.get(
            transactions_endpoint,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        api_payload = response.json()

    except requests.exceptions.RequestException as error:
        return (
            json.dumps({
                "status": "error",
                "stage": "api_request",
                "message": str(error)
            }),
            500,
            {"Content-Type": "application/json"},
        )

    if api_payload.get("status") != "success":
        return (
            json.dumps({
                "status": "error",
                "stage": "api_response_validation",
                "message": "External API did not return success status.",
                "api_payload": api_payload
            }),
            500,
            {"Content-Type": "application/json"},
        )

    records = api_payload.get("data", [])

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)

        safe_timestamp = run_timestamp.strftime("%Y%m%d_%H%M%S")
        blob_name = f"raw/transactions/transactions_{safe_timestamp}.json"

        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(api_payload, indent=2),
            content_type="application/json"
        )

    except Exception as error:
        return (
            json.dumps({
                "status": "error",
                "stage": "gcs_write",
                "message": str(error)
            }),
            500,
            {"Content-Type": "application/json"},
        )

    rows_to_insert = []

    for record in records:
        rows_to_insert.append({
            "transaction_id": record.get("transaction_id"),
            "customer_id": record.get("customer_id"),
            "transaction_date": record.get("transaction_date"),
            "amount": float(record.get("amount")) if record.get("amount") is not None else None,
            "merchant_name": record.get("merchant_name"),
            "payment_method": record.get("payment_method"),
            "status": record.get("status"),
            "ingestion_timestamp": ingestion_timestamp,
        })

    try:
        bigquery_client = bigquery.Client()
        table_id = f"{bigquery_client.project}.{bq_dataset}.{bq_table}"

        insert_errors = bigquery_client.insert_rows_json(
            table_id,
            rows_to_insert
        )

        if insert_errors:
            return (
                json.dumps({
                    "status": "error",
                    "stage": "bigquery_insert",
                    "message": "BigQuery insert returned errors.",
                    "errors": insert_errors
                }),
                500,
                {"Content-Type": "application/json"},
            )

    except Exception as error:
        return (
            json.dumps({
                "status": "error",
                "stage": "bigquery_insert",
                "message": str(error)
            }),
            500,
            {"Content-Type": "application/json"},
        )

    return (
        json.dumps({
            "status": "success",
            "message": "Transactions ingested successfully.",
            "records_received": len(records),
            "gcs_file": blob_name,
            "bigquery_table": f"{bq_dataset}.{bq_table}",
            "ingestion_timestamp": ingestion_timestamp
        }),
        200,
        {"Content-Type": "application/json"},
    )
