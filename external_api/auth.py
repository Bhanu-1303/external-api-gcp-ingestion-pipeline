import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv


load_dotenv()

EXPECTED_API_KEY = os.getenv("API_KEY")


def verify_api_key(x_api_key: str = Header(None)):
    """
    Verifies that the request contains a valid API key.
    """

    if not EXPECTED_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="API key is not configured on the server."
        )

    if x_api_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key."
        )

    return True
