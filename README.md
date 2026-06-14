# External API to GCP Ingestion Pipeline

## Project Overview

This project demonstrates a scheduled data ingestion pipeline where transaction data stored outside GCP is exposed through a FastAPI service and ingested into Google Cloud Platform using Cloud Scheduler and Cloud Run Functions.

The pipeline stores raw API responses in Google Cloud Storage and loads structured transaction records into BigQuery. It also uses BigQuery MERGE logic to maintain an idempotent final table and prevent duplicate records.

## Architecture

CSV Source  
→ FastAPI External API  
→ ngrok Public URL  
→ Cloud Scheduler  
→ Cloud Run Function  
→ Cloud Storage Raw Layer  
→ BigQuery Raw Table  
→ BigQuery Final Table using MERGE

## Tools Used

- Python
- FastAPI
- Uvicorn
- ngrok
- Google Cloud Run Functions
- Google Cloud Scheduler
- Google Cloud Storage
- BigQuery
- GitHub

## Data Flow

1. FastAPI reads transaction data from a local CSV file.
2. ngrok exposes the local FastAPI API through a public HTTPS URL.
3. Cloud Scheduler triggers the Cloud Run function every 15 minutes.
4. Cloud Run calls the external FastAPI `/transactions` endpoint using an API key.
5. Raw API response is saved to Google Cloud Storage.
6. Structured records are inserted into BigQuery `raw_transactions`.
7. BigQuery MERGE updates `final_transactions` using `transaction_id`.

## BigQuery Tables

### raw_transactions

Stores every ingestion run. This table is append-only and may contain duplicate transaction IDs.

### final_transactions

Stores the latest unique transaction record per `transaction_id`.

## Idempotency

The pipeline uses BigQuery MERGE logic to prevent duplicate final records. Re-running the pipeline multiple times may increase the raw table count, but the final table remains deduplicated by `transaction_id`.

## Error Handling

The Cloud Run function returns structured error responses for:

- Missing environment variables
- External API request failures
- API response validation failures
- Cloud Storage write failures
- BigQuery raw insert failures
- BigQuery MERGE failures

## Environment Variables

```env
EXTERNAL_API_URL=your_ngrok_or_external_api_url
API_KEY=your_api_key_here
GCS_BUCKET_NAME=your_gcs_bucket_name
BQ_DATASET=external_api_pipeline
BQ_TABLE=raw_transactions
BQ_FINAL_TABLE=final_transactions