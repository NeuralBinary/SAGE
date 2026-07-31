from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import Settings
from .db_models import BusMessage, MessageAudit, PatternCandidate, Reference, ReferenceGrant, SemanticCache
from .patterns import PatternStore


def cleanup(db: Session, settings: Settings) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    cache_result = db.execute(
        delete(SemanticCache).where(
            SemanticCache.expires_at.is_not(None),
            SemanticCache.expires_at <= now,
        )
    )
    grant_result = db.execute(delete(ReferenceGrant).where(ReferenceGrant.expires_at.is_not(None), ReferenceGrant.expires_at <= now))
    orphan_refs = list(db.scalars(select(Reference.id).where(~Reference.id.in_(select(ReferenceGrant.ref_id)))))
    ref_result = db.execute(delete(Reference).where(Reference.id.in_(orphan_refs))) if orphan_refs else None
    bus_expired_result = db.execute(
        delete(BusMessage).where(
            BusMessage.expires_at.is_not(None),
            BusMessage.expires_at <= now,
            BusMessage.status != "acked",
        )
    )
    pattern_cutoff = now - timedelta(days=settings.pattern_candidate_retention_days)
    pattern_candidate_result = db.execute(
        delete(PatternCandidate).where(PatternCandidate.last_seen < pattern_cutoff)
    )
    cutoff = now - timedelta(days=settings.audit_retention_days)
    bus_audit_result = db.execute(
        delete(BusMessage).where(BusMessage.status == "acked", BusMessage.acked_at < cutoff)
    )
    audit_result = db.execute(delete(MessageAudit).where(MessageAudit.created_at < cutoff))
    pattern_gc = PatternStore(db, settings).garbage_collect()
    db.commit()
    return {
        "semantic_cache_deleted": int(cache_result.rowcount or 0),
        "expired_ref_grants_deleted": int(grant_result.rowcount or 0),
        "orphan_refs_deleted": int(ref_result.rowcount or 0) if ref_result is not None else 0,
        "expired_bus_messages_deleted": int(bus_expired_result.rowcount or 0),
        "acked_bus_messages_deleted": int(bus_audit_result.rowcount or 0),
        "audit_rows_deleted": int(audit_result.rowcount or 0),
        "pattern_candidates_deleted": int(pattern_candidate_result.rowcount or 0),
        **pattern_gc,
    }
