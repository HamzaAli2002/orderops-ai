"""Thin wrapper around the OrderOps AI FastAPI backend."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ApiError(Exception):
    pass


def _get(path: str):
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(f"Can't reach the backend at {API_BASE_URL}. Is it running?") from exc
    except requests.exceptions.HTTPError as exc:
        raise ApiError(f"Request failed: {exc}") from exc


def _post(path: str, payload: dict):
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(f"Can't reach the backend at {API_BASE_URL}. Is it running?") from exc
    except requests.exceptions.HTTPError as exc:
        raise ApiError(f"Request failed: {exc}") from exc


def get_revenue_recovery():
    return _get("/metrics/revenue-recovery")


def get_customers():
    return _get("/customers")


def get_products():
    return _get("/products")


def get_order(order_id: str):
    return _get(f"/orders/{order_id}")


def get_negotiations(order_id: str):
    return _get(f"/orders/{order_id}/negotiations")


def get_all_negotiations(limit: int = 50):
    return _get(f"/negotiations?limit={limit}")


def create_order(customer_id: str, items: list[dict]):
    return _post("/orders", {"customer_id": customer_id, "items": items})


def respond_to_negotiation(order_id: str, negotiation_id: str, decision: str):
    return _post(
        f"/orders/{order_id}/customer-response",
        {"negotiation_id": negotiation_id, "decision": decision},
    )
