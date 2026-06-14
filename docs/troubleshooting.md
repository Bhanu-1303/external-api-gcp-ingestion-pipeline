# Troubleshooting Notes

## API request error

Possible causes:
- FastAPI server is not running
- ngrok is not running
- ngrok URL changed
- API key mismatch

Fix:
- Start FastAPI
- Start ngrok
- Update EXTERNAL_API_URL in Cloud Run if ngrok URL changed
- Ensure API_KEY matches local .env

## GCS write error

Possible cause:
- Cloud Run service account does not have permission to write to the bucket

Fix:
- Grant Storage Object Creator role to the Cloud Run service account on the GCS bucket

## BigQuery insert error

Possible cause:
- Cloud Run service account does not have permission to insert into BigQuery

Fix:
- Grant BigQuery Data Editor role to the Cloud Run service account on the dataset

## Duplicate records

Raw table may contain duplicates because every run appends records.

Fix:
- Use final_transactions table with BigQuery MERGE logic based on transaction_id