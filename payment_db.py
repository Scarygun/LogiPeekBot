import logging
import json
import os
from datetime import datetime
from typing import Union

PAYMENTS_JSON_FILE = 'payments.json'

logger = logging.getLogger(__name__)

def _read_json(filepath: str, default_data: Union[dict, list]) -> Union[dict, list]:
    if not os.path.exists(filepath):
        return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading {filepath}: {e}")
        return default_data

def _write_json(filepath: str, data: Union[dict, list]):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error writing to {filepath}: {e}")

async def create_payment(user_id: int, full_name: str, photo_id: str, amount: int = 49000, duration_days: int = 30, backend_payment_id: str = None) -> str:
    payments = _read_json(PAYMENTS_JSON_FILE, [])
    
    # Generate simple ID
    payment_id = f"PAY-{int(datetime.now().timestamp())}-{user_id}"
    
    payment = {
        "id": payment_id,
        "backend_payment_id": backend_payment_id,
        "user_id": user_id,
        "full_name": full_name,
        "photo_id": photo_id,
        "amount": amount,
        "duration_days": duration_days,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "processed_at": None,
        "processed_by": None,
        "reject_reason": None
    }
    
    payments.append(payment)
    _write_json(PAYMENTS_JSON_FILE, payments)
    return payment_id

async def get_payment(payment_id: str) -> dict:
    payments = _read_json(PAYMENTS_JSON_FILE, [])
    return next((p for p in payments if p.get("id") == payment_id), None)

async def get_pending_backend_payments() -> list:
    payments = _read_json(PAYMENTS_JSON_FILE, [])
    return [p for p in payments if p.get("backend_payment_id") and p.get("status") in ("pending", "awaiting_review")]

async def update_payment_status(payment_id: str, status: str, admin_id: int = 0, reason: str = None) -> bool:
    payments = _read_json(PAYMENTS_JSON_FILE, [])
    for p in payments:
        if p.get("id") == payment_id or p.get("backend_payment_id") == payment_id:
            p["status"] = status
            p["processed_at"] = datetime.now().isoformat()
            p["processed_by"] = admin_id
            if reason:
                p["reject_reason"] = reason
            _write_json(PAYMENTS_JSON_FILE, payments)
            return True
    return False

