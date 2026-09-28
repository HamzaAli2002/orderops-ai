"""Fraud/risk scoring service. Replace stub logic with a real model or rules engine."""

import random


async def compute_risk_score(order_id: str, customer_id: str) -> float:
    """
    TODO: Replace with real scoring - order value vs. customer history,
    shipping/billing mismatch, velocity checks, device fingerprinting, etc.
    """
    return round(random.uniform(0.0, 1.0), 2)
