# bc_client.py
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import quote
from .bc_config import BC_BASE_URL, BC_COMPANY

from .bc_config import (
    BC_BASE_URL,
    BC_COMPANY,
    BC_USERNAME,
    BC_PASSWORD,
)

def bc_url(resource: str) -> str:
    company = quote(BC_COMPANY)   # <-- encode ที่นี่
    return f"{BC_BASE_URL}/Company('{company}')/{resource}"

def bc_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def bc_auth():
    return HTTPBasicAuth(BC_USERNAME, BC_PASSWORD)
