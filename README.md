# External API to GCP Ingestion Pipeline

## Project Overview

This project demonstrates a scheduled data ingestion pipeline where transaction data stored outside GCP is exposed through a FastAPI service and ingested into Google Cloud Platform using Cloud Scheduler and Cloud Functions.

The pipeline stores raw API responses in Google Cloud Storage and structured transaction records in BigQuery.

## Architecture

CSV Source → FastAPI External API → ngrok Public URL → Cloud Scheduler → Cloud Function → GCS + BigQuery

## Tools Used

- Python
- FastAPI
- Uvicorn
- ngrok
- Google Cloud Scheduler
- Google Cloud Functions
- Google Cloud Storage
- BigQuery
- GitHub

## Project Structure

```text
external-api-gcp-ingestion-pipeline/
├── external_api/
├── gcp_function/
├── data/
├── sql/
├── docs/
├── tests/
├── requirements.txt
├── .gitignore
├── .env.example
└── README.md