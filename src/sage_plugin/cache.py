from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from .db_models import SemanticCache


def cache_key(value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


class CacheStore:
    def __init__(self, db: Session, ttl_seconds: int = 3600) -> None:
        self.db = db
        self.ttl_seconds = ttl_seconds

    def get(self, key: str, fingerprint: str) -> SemanticCache | None:
        item = self.db.get(SemanticCache, key)
        if item is None or item.codebook_fingerprint != fingerprint:
            return None
        if item.expires_at is not None:
            expires = item.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires <= datetime.now(timezone.utc):
                return None
        item.hit_count += 1
        return item

    def put(self, key: str, packet: dict[str, Any], decisions: list[dict[str, Any]], fingerprint: str) -> SemanticCache:
        item = self.db.get(SemanticCache, key)
        if item is None:
            item = SemanticCache(
                key=key,
                packet=packet,
                decisions=decisions,
                codebook_fingerprint=fingerprint,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
            )
            self.db.add(item)
        else:
            item.packet = packet
            item.decisions = decisions
            item.codebook_fingerprint = fingerprint
            item.expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)
        self.db.flush()
        return item
