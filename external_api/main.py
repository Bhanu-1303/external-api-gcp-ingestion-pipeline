from fastapi import FastAPI, HTTPException, Depends
from external_api.csv_reader import read_transactions_from_csv
from external_api.auth import verify_api_key


app = FastAPI(
    title="External Transactions API",
    description="API that exposes transaction records from an external CSV source.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "External Transactions API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "external-transactions-api"
    }


@app.get("/transactions")
def get_transactions(is_authorized: bool = Depends(verify_api_key)):
    try:
        transactions = read_transactions_from_csv()

        return {
            "status": "success",
            "record_count": len(transactions),
            "data": transactions
        }

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(error)}")
