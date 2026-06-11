from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE_PATH = BASE_DIR / "data" / "sample_transactions.csv"


def read_transactions_from_csv():
    """
    Reads transaction records from a CSV file and returns them as a list of dictionaries.
    """

    if not CSV_FILE_PATH.exists():
        raise FileNotFoundError(f"CSV file not found at: {CSV_FILE_PATH}")

    df = pd.read_csv(CSV_FILE_PATH)

    required_columns = [
        "transaction_id",
        "customer_id",
        "transaction_date",
        "amount",
        "merchant_name",
        "payment_method",
        "status",
    ]

    missing_columns = [
        col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    df = df.dropna(
        subset=["transaction_id", "customer_id", "transaction_date", "amount"])

    return df.to_dict(orient="records")
