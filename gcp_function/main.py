import json
import logging
import os
from datetime import datetime, timezone

import functions_framework
import requests
from google.cloud import bigquery
from google.cloud import storage


logging.basicConfig(level=logging.INFO)


@functions_framework.http
def ingest_transactions(request):
    """
    Cloud Run Function entry point.

    This function:
    1. Calls the external FastAPI transactions endpoint.
    2. Stores the raw API response in Cloud Storage.
    3. Inserts structured transaction rows into BigQuery raw table.
    4. Merges latest records into BigQuery final table to prevent duplicates.
    """

    logging.info("Starting external transactions ingestion pipeline.")

    external_api_url = os.environ.get("EXTERNAL_API_URL")
    api_key = os.environ.get("API_KEY")
    gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME")
    bq_dataset = os.environ.get("BQ_DATASET")
    bq_table = os.environ.get("BQ_TABLE")
    bq_final_table = os.environ.get("BQ_FINAL_TABLE")

    required_env_vars = {
        "EXTERNAL_API_URL": external_api_url,
        "API_KEY": api_key,
        "GCS_BUCKET_NAME": gcs_bucket_name,
        "BQ_DATASET": bq_dataset,
        "BQ_TABLE": bq_table,
        "BQ_FINAL_TABLE": bq_final_table,
    }

    missing_env_vars = [
        name for name, value in required_env_vars.items()
        if not value
    ]

    if missing_env_vars:
        logging.error(
            "Missing required environment variables: %s", missing_env_vars)
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
        logging.info("Calling external API: %s", transactions_endpoint)

        response = requests.get(
            transactions_endpoint,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        api_payload = response.json()

        logging.info("External API call successful.")

    except requests.exceptions.RequestException as error:
        logging.exception("External API request failed.")
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
        logging.error("External API returned non-success response.")
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
    logging.info("Records received from API: %s", len(records))

    if not records:
        logging.warning("External API returned zero records.")
        return (
            json.dumps({
                "status": "success",
                "message": "No records received from external API.",
                "records_received": 0
            }),
            200,
            {"Content-Type": "application/json"},
        )

    try:
        logging.info("Writing raw API response to GCS bucket: %s",
                     gcs_bucket_name)

        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)

        safe_timestamp = run_timestamp.strftime("%Y%m%d_%H%M%S")
        blob_name = f"raw/transactions/transactions_{safe_timestamp}.json"

        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(api_payload, indent=2),
            content_type="application/json"
        )

        logging.info("Raw API response written to GCS: %s", blob_name)

    except Exception as error:
        logging.exception("Failed to write raw API response to GCS.")
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

        raw_table_id = f"{bigquery_client.project}.{bq_dataset}.{bq_table}"
        final_table_id = f"{bigquery_client.project}.{bq_dataset}.{bq_final_table}"

        logging.info(
            "Inserting records into BigQuery raw table: %s", raw_table_id)

        insert_errors = bigquery_client.insert_rows_json(
            raw_table_id,
            rows_to_insert
        )

        if insert_errors:
            logging.error(
                "BigQuery raw insert returned errors: %s", insert_errors)
            return (
                json.dumps({
                    "status": "error",
                    "stage": "bigquery_raw_insert",
                    "message": "BigQuery insert returned errors.",
                    "errors": insert_errors
                }),
                500,
                {"Content-Type": "application/json"},
            )

        logging.info("Inserted %s records into BigQuery raw table.",
                     len(rows_to_insert))

    except Exception as error:
        logging.exception("Failed to insert records into BigQuery raw table.")
        return (
            json.dumps({
                "status": "error",
                "stage": "bigquery_raw_insert",
                "message": str(error)
            }),
            500,
            {"Content-Type": "application/json"},
        )

    try:
        logging.info(
            "Running BigQuery MERGE into final table: %s", final_table_id)

        merge_sql = f"""
        MERGE `{final_table_id}` AS target
        USING (
          SELECT
            transaction_id,
            customer_id,
            transaction_date,
            amount,
            merchant_name,
            payment_method,
            status,
            ingestion_timestamp
          FROM `{raw_table_id}`
          QUALIFY ROW_NUMBER() OVER (
            PARTITION BY transaction_id
            ORDER BY ingestion_timestamp DESC
          ) = 1
        ) AS source
        ON target.transaction_id = source.transaction_id

        WHEN MATCHED THEN
          UPDATE SET
            customer_id = source.customer_id,
            transaction_date = source.transaction_date,
            amount = source.amount,
            merchant_name = source.merchant_name,
            payment_method = source.payment_method,
            status = source.status,
            ingestion_timestamp = source.ingestion_timestamp

        WHEN NOT MATCHED THEN
          INSERT (
            transaction_id,
            customer_id,
            transaction_date,
            amount,
            merchant_name,
            payment_method,
            status,
            ingestion_timestamp
          )
          VALUES (
            source.transaction_id,
            source.customer_id,
            source.transaction_date,
            source.amount,
            source.merchant_name,
            source.payment_method,
            source.status,
            source.ingestion_timestamp
          )
        """

        merge_job = bigquery_client.query(merge_sql)
        merge_job.result()

        logging.info("BigQuery MERGE completed successfully.")

    except Exception as error:
        logging.exception("Failed to merge records into BigQuery final table.")
        return (
            json.dumps({
                "status": "error",
                "stage": "bigquery_merge",
                "message": str(error)
            }),
            500,
            {"Content-Type": "application/json"},
        )

    logging.info("Pipeline completed successfully.")

    return (
        json.dumps({
            "status": "success",
            "message": "Transactions ingested and merged successfully.",
            "records_received": len(records),
            "gcs_file": blob_name,
            "raw_bigquery_table": f"{bq_dataset}.{bq_table}",
            "final_bigquery_table": f"{bq_dataset}.{bq_final_table}",
            "ingestion_timestamp": ingestion_timestamp
        }),
        200,
        {"Content-Type": "application/json"},
    )
