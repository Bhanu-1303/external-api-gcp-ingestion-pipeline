MERGE `external-api-gcp-ingestion.external_api_pipeline.final_transactions` AS target
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
FROM `external-api-gcp-ingestion.external_api_pipeline.raw_transactions`
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
  );