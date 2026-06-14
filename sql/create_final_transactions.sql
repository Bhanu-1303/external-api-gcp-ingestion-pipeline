CREATE TABLE
IF NOT EXISTS `external-api-gcp-ingestion.external_api_pipeline.final_transactions`
(
  transaction_id STRING,
  customer_id STRING,
  transaction_date DATE,
  amount FLOAT64,
  merchant_name STRING,
  payment_method STRING,
  status STRING,
  ingestion_timestamp TIMESTAMP
);