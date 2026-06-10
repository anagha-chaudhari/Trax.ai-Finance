import json
import redis
from typing import Optional, Any
from utils.config import settings


def get_redis_client() -> Optional[redis.Redis]:
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()   
        return client
    except Exception:
        return None

redis_client = get_redis_client()


def cache_set(key: str, value: Any, expire_seconds: int = 3600) -> bool:
    if redis_client is None:
        return False
    try:
        redis_client.setex(key, expire_seconds, json.dumps(value))
        return True
    except Exception:
        return False

def cache_get(key: str) -> Optional[Any]:
    if redis_client is None:
        return None
    try:
        raw_value = redis_client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)
    except Exception:
        return None

def cache_delete(key: str) -> bool:
    if redis_client is None:
        return False
    try:
        redis_client.delete(key)
        return True
    except Exception:
        return False

# Job status helpers

JOB_TTL = 600


def set_job_status(job_id: str, status: str) -> None:
    cache_set(f"job:{job_id}:status", status, expire_seconds=JOB_TTL)


def get_job_status(job_id: str) -> Optional[str]:
    return cache_get(f"job:{job_id}:status")


def set_job_result(job_id: str, result: Any) -> None:
    cache_set(f"job:{job_id}:result", result, expire_seconds=JOB_TTL)


def get_job_result(job_id: str) -> Optional[Any]:
    return cache_get(f"job:{job_id}:result")