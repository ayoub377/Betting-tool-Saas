import os
import requests

API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
BASE_URL = "https://api.lemonsqueezy.com/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}


def list_products():
    res = requests.get(f"{BASE_URL}/products?filter[store_id]={STORE_ID}", headers=HEADERS)
    res.raise_for_status()
    return res.json()["data"]


def create_checkout(email: str, variant_id: int):
    data = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {"email": email},
                "custom_price": None,
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": STORE_ID}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        }
    }

    res = requests.post(f"{BASE_URL}/checkouts", headers=HEADERS, json=data)
    res.raise_for_status()
    return res.json()["data"]["attributes"]["url"]
