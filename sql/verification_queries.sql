-- Count raw records
SELECT COUNT(*) AS raw_count
FROM `external-api-gcp-ingestion.external_api_pipeline.raw_transactions`;

-- Count final records
SELECT COUNT(*) AS final_count
FROM `external-api-gcp-ingestion.external_api_pipeline.final_transactions`;

-- Check duplicates in final table
SELECT
    transaction_id,
    COUNT(*) AS duplicate_count
FROM `external-api-gcp-ingestion.external_api_pipeline.final_transactions`
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- View latest final records
SELECT *
FROM `external-api-gcp-ingestion.external_api_pipeline.final_transactions`
ORDER BY ingestion_timestamp DESC;