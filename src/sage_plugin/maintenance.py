from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import Settings
from .db_models import BusMessage, IdempotencyRecord, MessageAudit, PatternCandidate, QuotaCounter, Reference, ReferenceGrant, SemanticCache, SharedState
from .reachability import reachable_states, reference_roots
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
    roots = reference_roots(db, retain_audit=settings.gc_retain_audit_replay)
    all_refs = set(db.scalars(select(Reference.id)))
    orphan_refs = sorted(all_refs - roots)
    ref_result = db.execute(delete(Reference).where(Reference.id.in_(orphan_refs))) if orphan_refs else None
    bus_expired_result = db.execute(
        delete(BusMessage).where(
            BusMessage.expires_at.is_not(None),
            BusMessage.expires_at <= now,
            BusMessage.status != "acked",
        )
    )
    state_cutoff = now - timedelta(days=settings.state_retention_days)
    reachable = reachable_states(db, retain_audit=settings.gc_retain_audit_replay)
    stale_states = list(db.scalars(select(SharedState.id).where(SharedState.created_at < state_cutoff)))
    orphan_states = sorted(set(stale_states) - reachable)
    state_result = db.execute(delete(SharedState).where(SharedState.id.in_(orphan_states))) if orphan_states else None
    pattern_cutoff = now - timedelta(days=settings.pattern_candidate_retention_days)
    pattern_candidate_result = db.execute(
        delete(PatternCandidate).where(PatternCandidate.last_seen < pattern_cutoff)
    )
    cutoff = now - timedelta(days=settings.audit_retention_days)
    bus_audit_result = db.execute(
        delete(BusMessage).where(BusMessage.status == "acked", BusMessage.acked_at < cutoff)
    )
    audit_result = db.execute(delete(MessageAudit).where(MessageAudit.created_at < cutoff))
    idempotency_result = db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.expires_at.is_not(None), IdempotencyRecord.expires_at <= now))
    quota_cutoff = now - timedelta(seconds=settings.quota_window_seconds * 2)
    quota_result = db.execute(delete(QuotaCounter).where(QuotaCounter.window_start < quota_cutoff))
    pattern_gc = PatternStore(db, settings).garbage_collect()
    db.commit()
    return {
        "semantic_cache_deleted": int(cache_result.rowcount or 0),
        "expired_ref_grants_deleted": int(grant_result.rowcount or 0),
        "orphan_refs_deleted": int(ref_result.rowcount or 0) if ref_result is not None else 0,
        "expired_bus_messages_deleted": int(bus_expired_result.rowcount or 0),
        "orphan_states_deleted": int(state_result.rowcount or 0) if state_result is not None else 0,
        "acked_bus_messages_deleted": int(bus_audit_result.rowcount or 0),
        "audit_rows_deleted": int(audit_result.rowcount or 0),
        "pattern_candidates_deleted": int(pattern_candidate_result.rowcount or 0),
        "idempotency_records_deleted": int(idempotency_result.rowcount or 0),
        "quota_counters_deleted": int(quota_result.rowcount or 0),
        **pattern_gc,
    }
