from __future__ import annotations

from datetime import timezone
from typing import Any

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .a2a_adapter import agent_card, agent_card_extension, pack_data_part, pack_message, unpack_data_part, unpack_message
from .bus import SemanticBus
from .conformance import run_tck
from .codebook import Codebook
from .codec import SageCodec
from .config import get_settings
from .db import get_db
from .db_models import Concept, Contradiction, MessageAudit, PatternCandidate, ReceiverKnowledge
from .facts import FactStore
from .federation import FederationStore
from .inspector import Inspector
from .routing import SemanticPubSub, SemanticRouter
from .evals import run_eval
from .economics import run_sage_economics_benchmark, score_observed_runs
from .integrations import config_for, profiles
from .knowledge import KnowledgeStore
from .latent import pack_latent, unpack_latent
from .patterns import PatternStore
from .maintenance import cleanup
from .references import ReferenceAccessError, ReferenceExpiredError, ReferenceStore
from .protocol_spec import SAGE_PROTOCOL, SAGE_SUPPORTED_PROTOCOLS, SAGE_WIRE_VERSION, canonical_digest, validate_wire_v1, wire_schema
from .schemas import (
    A2APackRequest,
    A2AUnpackRequest,
    A2AMessagePackRequest,
    A2AMessageUnpackRequest,
    BusAckRequest,
    BusBatchAckRequest,
    BusContextItem,
    BusMessageResponse,
    Capabilities,
    ConceptAliasRequest,
    ConceptDeprecateRequest,
    ConceptRegisterRequest,
    ConceptResponse,
    DecodeRequest,
    DecodeResponse,
    EncodeRequest,
    EncodeResponse,
    EvalRequest,
    EconomicsBenchmarkRequest,
    ObservedEconomicsRequest,
    ExplainResponse,
    FeedbackRequest,
    CounterfactualPatternRequest,
    ContradictionResolveRequest,
    FactPutRequest,
    FactResponse,
    FactInvalidateRequest,
    SubscriptionRequest,
    PublishRequest,
    AgentCapabilityRequest,
    RouteRequest,
    FederationPeerRequest,
    FederationImportRequest,
    InspectorResponse,
    HandoffRequest,
    IntegrationConfigResponse,
    IntegrationProfile,
    LatentPackRequest,
    LatentPacket,
    LatentUnpackRequest,
    NativeTokenGateRequest,
    NativeTokenGateResponse,
    PatternCandidateResponse,
    PatternObserveRequest,
    PatternResponse,
    PatternStatusRequest,
    NegotiateRequest,
    NegotiateResponse,
    ReceiveRequest,
    RefPolicyRequest,
    RefGrantRequest,
    ReplayResponse,
    ResolveRequest,
    SendRequest,
    StateCreateRequest,
    StatePatchRequest,
    StateResponse,
    StoreRequest,
    StoreResponse,
    TransportReceiveRequest,
    TransportResponse,
)
from .security import current_principal, enforce_agent_scope, require_api_key
from .state import StateStore

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
settings = get_settings()


def concept_response(c: Concept, db: Session | None = None) -> ConceptResponse:
    replacement_code = None
    if c.replacement_id:
        replacement = db.get(Concept, c.replacement_id) if db else None
        replacement_code = replacement.code if replacement else f"C{c.replacement_id:08X}"
    return ConceptResponse(
        code=c.code,
        codebook=c.codebook,
        canonical=c.canonical,
        description=c.description,
        seen_count=c.seen_count,
        confidence=c.confidence,
        version=c.version,
        status=c.status,
        replacement_code=replacement_code,
    )


def bus_response(item: Any) -> BusMessageResponse:
    return BusMessageResponse(
        message_id=item.id,
        packet_id=item.packet_id,
        sender=item.sender,
        receiver=item.receiver,
        workspace=item.workspace,
        run_id=item.run_id,
        correlation_id=item.correlation_id,
        priority=item.priority,
        status=item.status,
        wire=item.wire,
        strategy=item.strategy,
        estimated_tokens=item.estimated_tokens,
        wire_bytes=item.wire_bytes,
        expires_at=item.expires_at.isoformat() if item.expires_at else None,
        created_at=item.created_at.isoformat(),
    )


@router.post("/bus/handoff", response_model=BusMessageResponse)
def bus_handoff(req: HandoffRequest, db: Session = Depends(get_db)) -> BusMessageResponse:
    """Compress and durably enqueue a framework-neutral agent-to-agent handoff."""
    sender = enforce_agent_scope(actor=req.sender, workspace=req.workspace)
    try:
        bus = SemanticBus(db, settings)
        if req.refs:
            item = bus.forward_refs(
                receiver=req.receiver, refs=req.refs, sender=sender, workspace=req.workspace, run_id=req.run_id,
                correlation_id=req.correlation_id, priority=req.priority, ttl_seconds=req.ttl_seconds, source_ids=req.source_ids,
            )
        else:
            if req.content is None:
                raise ValueError("content or refs is required")
            item = bus.handoff(
                receiver=req.receiver, content=req.content, sender=sender, act=req.act, workspace=req.workspace,
                run_id=req.run_id, correlation_id=req.correlation_id, priority=req.priority, ttl_seconds=req.ttl_seconds,
                budget_tokens=req.budget_tokens, source_ids=req.source_ids,
            )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return bus_response(item)


@router.get("/bus/pull/{receiver}", response_model=list[BusMessageResponse])
def bus_pull(
    receiver: str,
    workspace: str = Query(default="default"),
    limit: int = Query(default=20, ge=1, le=100),
    claim: bool = Query(default=True),
    budget_tokens: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[BusMessageResponse]:
    enforce_agent_scope(actor=receiver, workspace=workspace)
    items = SemanticBus(db, settings).pull(
        receiver=receiver, workspace=workspace, limit=limit, claim=claim, budget_tokens=budget_tokens
    )
    if claim:
        db.commit()
    return [bus_response(item) for item in items]


@router.get("/bus/context/{receiver}", response_model=list[BusContextItem])
def bus_context(
    receiver: str,
    workspace: str = Query(default="default"),
    limit: int = Query(default=20, ge=1, le=100),
    budget_tokens: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[BusContextItem]:
    receiver = enforce_agent_scope(actor=receiver, workspace=workspace)
    bus = SemanticBus(db, settings)
    items = bus.pull(
        receiver=receiver,
        workspace=workspace,
        limit=limit,
        claim=True,
        budget_tokens=budget_tokens,
    )
    result: list[BusContextItem] = []
    for item in items:
        decoded = bus.codec.decode(
            bus.codec.expand(item.wire),
            False,
            receiver=receiver,
            workspace=workspace,
            acknowledge=False,
        )
        result.append(
            BusContextItem(
                message_id=item.id,
                packet_id=item.packet_id,
                sender=item.sender,
                receiver=item.receiver,
                workspace=item.workspace,
                run_id=item.run_id,
                correlation_id=item.correlation_id,
                act=decoded.act,
                concepts=decoded.concepts,
                literals=decoded.literals,
                references=decoded.references,
                provenance=decoded.provenance,
                base_state=decoded.base_state,
                delta=decoded.delta,
                resolved_state=decoded.resolved_state,
                strategy=item.strategy,
                estimated_tokens=item.estimated_tokens,
                wire_bytes=item.wire_bytes,
            )
        )
    db.commit()
    return result


@router.post("/bus/ack-batch", response_model=list[BusMessageResponse])
def bus_ack_batch(
    req: BusBatchAckRequest, db: Session = Depends(get_db)
) -> list[BusMessageResponse]:
    receiver = enforce_agent_scope(actor=req.receiver, workspace=req.workspace)
    bus = SemanticBus(db, settings)
    items = []
    try:
        for message_id in dict.fromkeys(req.message_ids):
            items.append(bus.ack(message_id, receiver=receiver, workspace=req.workspace))
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        db.rollback()
        raise HTTPException(404, "message not found") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return [bus_response(item) for item in items]


@router.post("/bus/{message_id}/ack", response_model=BusMessageResponse)
def bus_ack(
    message_id: str, req: BusAckRequest, db: Session = Depends(get_db)
) -> BusMessageResponse:
    enforce_agent_scope(actor=req.receiver, workspace=req.workspace)
    try:
        item = SemanticBus(db, settings).ack(
            message_id, receiver=req.receiver, workspace=req.workspace
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "message not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return bus_response(item)


@router.post("/bus/{message_id}/nack", response_model=BusMessageResponse)
def bus_nack(
    message_id: str, req: BusAckRequest, db: Session = Depends(get_db)
) -> BusMessageResponse:
    enforce_agent_scope(actor=req.receiver, workspace=req.workspace)
    try:
        item = SemanticBus(db, settings).nack(
            message_id, receiver=req.receiver, workspace=req.workspace
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "message not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return bus_response(item)


@router.post("/a2a/pack")
def a2a_pack(req: A2APackRequest) -> dict[str, Any]:
    return pack_data_part(req.wire)


@router.post("/a2a/unpack")
def a2a_unpack(req: A2AUnpackRequest) -> dict[str, Any]:
    try:
        return {"wire": unpack_data_part(req.part)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/a2a/message/pack")
def a2a_message_pack(req: A2AMessagePackRequest) -> dict[str, Any]:
    try:
        return pack_message(
            req.wire,
            message_id=req.message_id,
            role=req.role,
            context_id=req.context_id,
            task_id=req.task_id,
            metadata=req.metadata or None,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/a2a/message/unpack")
def a2a_message_unpack(req: A2AMessageUnpackRequest) -> dict[str, Any]:
    try:
        return {"wire": unpack_message(req.message)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/a2a/extension")
def a2a_extension() -> dict[str, Any]:
    return agent_card_extension()


@router.get("/a2a/agent-card")
def a2a_agent_card(
    url: str = Query(..., description="Public A2A 1.0 endpoint URL"),
    name: str = Query(default="SAGE-enabled agent"),
    description: str = Query(default="Agent supporting SAGE semantic payloads"),
    version: str = Query(default="1.0.0"),
    protocol_binding: str = Query(default="HTTP+JSON"),
) -> dict[str, Any]:
    if settings.env == "production" and not url.lower().startswith("https://"):
        raise HTTPException(422, "production A2A interface URLs must use HTTPS")
    return agent_card(
        name=name,
        description=description,
        url=url,
        version=version,
        protocol_binding=protocol_binding,
    )


@router.get("/protocol")
def protocol_info() -> dict[str, Any]:
    return {
        "protocol": SAGE_PROTOCOL,
        "wire_version": SAGE_WIRE_VERSION,
        "supported_protocols": list(SAGE_SUPPORTED_PROTOCOLS),
        "canonical_digest": "sha256(canonical-msgpack)",
        "frozen_line": "0.1.x",
    }


@router.get("/protocol/wire-schema")
def protocol_wire_schema() -> dict[str, Any]:
    return wire_schema()


@router.post("/protocol/validate")
def protocol_validate(wire: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_wire_v1(wire)
    except (ValidationError, ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"valid": True, "protocol": SAGE_PROTOCOL, "digest": canonical_digest(wire)}


@router.get("/protocol/tck")
def protocol_tck() -> dict[str, Any]:
    return run_tck().as_dict()


@router.get("/integrations", response_model=list[IntegrationProfile])
def list_integrations() -> list[IntegrationProfile]:
    return profiles()


@router.get("/integrations/{platform}", response_model=IntegrationConfigResponse)
def integration_config(
    platform: str,
    base_url: str = Query(..., min_length=8),
    agent_id: str = Query(..., min_length=1),
) -> IntegrationConfigResponse:
    try:
        return config_for(platform, base_url, agent_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/send", response_model=EncodeResponse)
def send(req: SendRequest, db: Session = Depends(get_db)) -> EncodeResponse:
    """Primary SAGE transport: receiver-aware, budget-constrained communication."""
    req.sender = enforce_agent_scope(actor=req.sender, workspace=req.workspace)
    try:
        return SageCodec(db, settings).encode(req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        status = 413 if str(exc).startswith("payload exceeds") else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/transport/send", response_model=TransportResponse)
def transport_send(req: SendRequest, db: Session = Depends(get_db)) -> TransportResponse:
    req.sender = enforce_agent_scope(actor=req.sender, workspace=req.workspace)
    codec = SageCodec(db, settings)
    try:
        result = codec.encode(req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        status = 413 if str(exc).startswith("payload exceeds") else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return TransportResponse(
        packet_id=result.packet.id or "",
        wire=codec.compact(result.packet),
        strategy=result.strategy,
        estimated_tokens=result.estimated_tokens,
        output_bytes=result.output_bytes_msgpack,
        cache_hit=result.cache_hit,
    )


@router.post("/transport/receive", response_model=DecodeResponse)
def transport_receive(req: TransportReceiveRequest, db: Session = Depends(get_db)) -> DecodeResponse:
    req.receiver = enforce_agent_scope(actor=req.receiver, workspace=req.workspace)
    codec = SageCodec(db, settings)
    packet = codec.expand(req.wire)
    return codec.decode(
        packet,
        req.resolve_refs,
        receiver=req.receiver,
        workspace=req.workspace,
        acknowledge=req.acknowledge,
    )


@router.post("/receive", response_model=DecodeResponse)
def receive(req: ReceiveRequest, db: Session = Depends(get_db)) -> DecodeResponse:
    req.receiver = enforce_agent_scope(actor=req.receiver, workspace=req.workspace)
    return SageCodec(db, settings).decode(
        req.packet,
        req.resolve_refs,
        receiver=req.receiver,
        workspace=req.workspace,
        acknowledge=req.acknowledge,
    )


@router.post("/encode", response_model=EncodeResponse)
def encode(req: EncodeRequest, db: Session = Depends(get_db)) -> EncodeResponse:
    try:
        return SageCodec(db, settings).encode(req)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        status = 413 if str(exc).startswith("payload exceeds") else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/decode", response_model=DecodeResponse)
def decode(req: DecodeRequest, db: Session = Depends(get_db)) -> DecodeResponse:
    return SageCodec(db, settings).decode(
        req.packet,
        req.resolve_refs,
        receiver=req.receiver,
        workspace=req.workspace,
    )


@router.get("/explain/{packet_id}", response_model=ExplainResponse)
def explain(packet_id: str, db: Session = Depends(get_db)) -> ExplainResponse:
    item = db.scalar(select(MessageAudit).where(MessageAudit.packet_id == packet_id))
    if item is None:
        raise HTTPException(404, "packet not found")
    return ExplainResponse(
        packet_id=item.packet_id,
        strategy=item.strategy,
        decisions=item.decisions,
        provenance=item.provenance,
        cache_hit=item.cache_hit,
        input_bytes=item.input_bytes,
        output_bytes=item.output_bytes,
        estimated_tokens=item.estimated_tokens,
        budget_tokens=item.budget_tokens,
    )




@router.get("/inspect/{packet_id}", response_model=InspectorResponse)
def inspect_packet(packet_id: str, db: Session = Depends(get_db)) -> InspectorResponse:
    principal = current_principal()
    workspace = principal.workspace if principal.kind == "agent" else None
    actor = principal.agent if principal.kind == "agent" else None
    try:
        return InspectorResponse.model_validate(Inspector(db).packet(packet_id, workspace=workspace, actor=actor))
    except KeyError as exc:
        raise HTTPException(404, "packet not found") from exc


@router.get("/inspect/run/{run_id}")
def inspect_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    principal = current_principal()
    workspace = principal.workspace if principal.kind == "agent" else None
    actor = principal.agent if principal.kind == "agent" else None
    try:
        return Inspector(db).run(run_id, workspace=workspace, actor=actor)
    except KeyError as exc:
        raise HTTPException(404, "run not found") from exc


@router.post("/feedback/{packet_id}")
def feedback(packet_id: str, req: FeedbackRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.scalar(select(MessageAudit).where(MessageAudit.packet_id == packet_id))
    if item is None:
        raise HTTPException(404, "packet not found")
    item.task_success = req.task_success
    patterns = PatternStore(db, settings).record_feedback(item.decisions, req.task_success)
    db.commit()
    return {
        "packet_id": packet_id,
        "task_success": req.task_success,
        "patterns_updated": [PatternStore(db, settings).response(pattern) for pattern in patterns],
    }


@router.get("/runs/{run_id}/replay", response_model=ReplayResponse)
def replay(run_id: str, db: Session = Depends(get_db)) -> ReplayResponse:
    items = list(
        db.scalars(
            select(MessageAudit).where(MessageAudit.run_id == run_id).order_by(MessageAudit.created_at, MessageAudit.id)
        )
    )
    return ReplayResponse(
        run_id=run_id,
        packets=[
            {
                "packet_id": item.packet_id,
                "sender": item.sender,
                "receiver": item.receiver,
                "strategy": item.strategy,
                "packet": item.packet,
                "decisions": item.decisions,
                "task_success": item.task_success,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    )


@router.post("/refs", response_model=StoreResponse)
def store_ref(req: StoreRequest, db: Session = Depends(get_db)) -> StoreResponse:
    req.owner = enforce_agent_scope(actor=req.owner, workspace=req.workspace)
    try:
        item = ReferenceStore(db, settings).put(
            req.value,
            req.media_type,
            workspace=req.workspace,
            owner=req.owner,
            acl=req.acl,
            allowed_paths=req.allowed_paths,
            tier=req.tier,
            ttl_seconds=req.ttl_seconds,
            encrypt=req.encrypt,
            provenance=req.provenance.model_dump() if req.provenance else {},
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    grant = ReferenceStore(db, settings).grant_metadata(item.id, actor=req.owner, workspace=req.workspace, privileged=current_principal().is_service)
    db.commit()
    expires = grant.expires_at.isoformat() if grant.expires_at else None
    return StoreResponse(ref=item.id, byte_size=item.byte_size, tier=grant.tier, encrypted=item.ciphertext is not None, expires_at=expires)


@router.post("/refs/resolve")
def resolve_ref(req: ResolveRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    req.actor = enforce_agent_scope(actor=req.actor, workspace=req.workspace)
    store = ReferenceStore(db, settings)
    try:
        item = store.get(req.ref, actor=req.actor, workspace=req.workspace)
    except (ReferenceAccessError, ReferenceExpiredError) as exc:
        raise HTTPException(403 if isinstance(exc, ReferenceAccessError) else 410, str(exc)) from exc
    if item is None:
        raise HTTPException(404, "reference not found")
    grant = store.grant_metadata(item.id, actor=req.actor, workspace=req.workspace)
    return {
        "ref": item.id, "media_type": item.media_type,
        "value": store.resolve(item.id, actor=req.actor, workspace=req.workspace, fields=req.fields),
        "byte_size": item.byte_size, "tier": grant.tier, "provenance": grant.provenance,
        "allowed_paths": grant.allowed_paths, "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
    }


@router.get("/refs/{ref_id}")
def get_ref(
    ref_id: str,
    actor: str | None = Query(default=None),
    workspace: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return resolve_ref(ResolveRequest(ref=ref_id, actor=actor, workspace=workspace), db)


@router.post("/refs/{ref_id}/policy")
def ref_policy(ref_id: str, req: RefPolicyRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    req.actor = enforce_agent_scope(actor=req.actor, workspace=req.workspace)
    try:
        item = ReferenceStore(db, settings).policy(
            ref_id,
            actor=req.actor,
            workspace=req.workspace,
            tier=req.tier,
            ttl_seconds=req.ttl_seconds,
            invalidate=req.invalidate,
        )
    except ReferenceAccessError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "reference not found") from exc
    grant = ReferenceStore(db, settings).grant_metadata(item.id, actor=req.actor, workspace=req.workspace)
    db.commit()
    return {"ref": item.id, "tier": grant.tier, "invalidated": grant.invalidated_at is not None, "expires_at": grant.expires_at.isoformat() if grant.expires_at else None}


@router.post("/refs/{ref_id}/grant")
def ref_grant(ref_id: str, req: RefGrantRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    req.actor = enforce_agent_scope(actor=req.actor, workspace=req.workspace)
    store = ReferenceStore(db, settings)
    try:
        principal = current_principal()
        current = store.grant_metadata(
            ref_id,
            actor=req.actor,
            workspace=req.workspace,
            privileged=principal.is_service,
        )
        if not principal.is_service and current.owner != req.actor:
            raise ReferenceAccessError("only the owner or a service credential can delegate reference access")
        grant = store.grant(ref_id, workspace=req.workspace, owner=current.owner, acl=list(set(current.acl) | set(req.acl) | ({req.grantee} if req.grantee else set())), allowed_paths=req.allowed_paths or current.allowed_paths, tier=req.tier, ttl_seconds=req.ttl_seconds, provenance=current.provenance)
    except ReferenceAccessError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "reference not found") from exc
    db.commit()
    return {"ref": ref_id, "workspace": grant.workspace, "owner": grant.owner, "acl": grant.acl, "allowed_paths": grant.allowed_paths}


@router.post("/states", response_model=StateResponse)
def create_state(req: StateCreateRequest, db: Session = Depends(get_db)) -> StateResponse:
    req.created_by = enforce_agent_scope(actor=req.created_by, workspace=req.workspace)
    item = StateStore(db).create(
        req.value,
        workspace=req.workspace,
        created_by=req.created_by,
        provenance=req.provenance.model_dump() if req.provenance else {},
    )
    db.commit()
    return StateResponse(
        state=item.id,
        revision=item.revision,
        value=item.payload,
        parent=item.parent_id,
        provenance=item.provenance,
    )


@router.get("/states/{state_id}", response_model=StateResponse)
def get_state(
    state_id: str,
    workspace: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> StateResponse:
    enforce_agent_scope(actor=None, workspace=workspace)
    item = StateStore(db).get(state_id, workspace=workspace)
    if item is None:
        raise HTTPException(404, "state not found")
    return StateResponse(
        state=item.id,
        revision=item.revision,
        value=item.payload,
        parent=item.parent_id,
        provenance=item.provenance,
    )


@router.get("/states/{state_id}/lineage")
def state_lineage(
    state_id: str,
    workspace: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    enforce_agent_scope(actor=None, workspace=workspace)
    lineage = StateStore(db).lineage(state_id, workspace=workspace)
    if not lineage:
        raise HTTPException(404, "state not found")
    return [
        {"state": item.id, "revision": item.revision, "parent": item.parent_id, "value": item.payload}
        for item in lineage
    ]


@router.post("/states/transition", response_model=StateResponse)
def transition(req: StatePatchRequest, db: Session = Depends(get_db)) -> StateResponse:
    req.created_by = enforce_agent_scope(actor=req.created_by, workspace=req.workspace)
    try:
        item, patch = StateStore(db).transition(
            req.base,
            req.value,
            is_patch=req.mode == "patch",
            workspace=req.workspace,
            created_by=req.created_by,
            provenance=req.provenance.model_dump() if req.provenance else {},
        )
    except KeyError as exc:
        raise HTTPException(404, "base state not found") from exc
    db.commit()
    return StateResponse(
        state=item.id,
        revision=item.revision,
        value=item.payload,
        parent=item.parent_id,
        delta=patch,
        provenance=item.provenance,
    )


@router.post("/concepts", response_model=ConceptResponse)
def register_concept(req: ConceptRegisterRequest, db: Session = Depends(get_db)) -> ConceptResponse:
    try:
        item = Codebook(db, settings).register(
            req.codebook or settings.codebook,
            req.canonical,
            req.description,
            req.aliases,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return concept_response(item, db)


@router.post("/concepts/{code}/aliases")
def add_alias(code: str, req: ConceptAliasRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        item = Codebook(db, settings).add_alias(code, req.alias)
    except KeyError as exc:
        raise HTTPException(404, "concept not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return {"code": code, "alias": item.alias}


@router.post("/concepts/{code}/deprecate", response_model=ConceptResponse)
def deprecate_concept(code: str, req: ConceptDeprecateRequest, db: Session = Depends(get_db)) -> ConceptResponse:
    cb = Codebook(db, settings)
    try:
        concept_id = int(code[1:], 16)
    except (ValueError, IndexError) as exc:
        raise HTTPException(404, "concept not found") from exc
    raw = db.get(Concept, concept_id)
    if raw is None:
        raise HTTPException(404, "concept not found")
    try:
        item = cb.deprecate(code, req.replacement_code)
    except (KeyError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return concept_response(item, db)


@router.get("/concepts", response_model=list[ConceptResponse])
def list_concepts(
    codebook: str | None = None,
    limit: int = 100,
    include_deprecated: bool = False,
    db: Session = Depends(get_db),
) -> list[ConceptResponse]:
    limit = max(1, min(limit, 1000))
    cb = codebook or settings.codebook
    stmt = select(Concept).where(Concept.codebook == cb)
    if not include_deprecated:
        stmt = stmt.where(Concept.status == "active")
    items = db.scalars(stmt.order_by(Concept.id).limit(limit))
    return [concept_response(c, db) for c in items]


@router.post("/patterns/observe", response_model=list[PatternResponse])
def observe_patterns(req: PatternObserveRequest, db: Session = Depends(get_db)) -> list[PatternResponse]:
    """Mine higher-order semantic patterns without sending a packet."""
    from .compiler import compile_content

    store = PatternStore(db, settings)
    codebook = req.codebook or settings.codebook
    promoted = store.observe_units(codebook, compile_content(req.content)[: settings.max_message_atoms])
    db.commit()
    return [PatternResponse.model_validate(store.response(item)) for item in promoted]


@router.get("/patterns", response_model=list[PatternResponse])
def list_patterns(
    codebook: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[PatternResponse]:
    store = PatternStore(db, settings)
    items = store.list(codebook or settings.codebook, status=status)[:limit]
    return [PatternResponse.model_validate(store.response(item)) for item in items]


@router.get("/patterns/candidates", response_model=list[PatternCandidateResponse])
def list_pattern_candidates(
    codebook: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[PatternCandidateResponse]:
    items = PatternStore(db, settings).candidates(codebook or settings.codebook)[:limit]
    return [
        PatternCandidateResponse(
            codebook=item.codebook,
            signature=item.signature,
            canonical=item.canonical,
            composition=item.composition,
            relation_structure=item.relation_structure,
            occurrence_count=item.occurrence_count,
            estimated_savings_bytes=item.estimated_savings_bytes,
            semantic_variance=item.semantic_variance,
        )
        for item in items
    ]


@router.get("/patterns/{pattern_id}", response_model=PatternResponse)
def get_pattern(pattern_id: str, db: Session = Depends(get_db)) -> PatternResponse:
    store = PatternStore(db, settings)
    item = store.get(pattern_id)
    if item is None:
        raise HTTPException(404, "pattern not found")
    return PatternResponse.model_validate(store.response(item))


@router.post("/patterns/{pattern_id}/status", response_model=PatternResponse)
def set_pattern_status(
    pattern_id: str, req: PatternStatusRequest, db: Session = Depends(get_db)
) -> PatternResponse:
    store = PatternStore(db, settings)
    try:
        item = store.set_status(pattern_id, req.status)
    except KeyError as exc:
        raise HTTPException(404, "pattern not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return PatternResponse.model_validate(store.response(item))


@router.post("/patterns/{pattern_id}/counterfactual", response_model=PatternResponse)
def pattern_counterfactual(pattern_id: str, req: CounterfactualPatternRequest, db: Session = Depends(get_db)) -> PatternResponse:
    store = PatternStore(db, settings)
    try:
        item = store.record_counterfactual(pattern_id, full_success=req.full_success, compressed_success=req.compressed_success, semantic_fidelity=req.semantic_fidelity, receiver=req.receiver, model=req.model, workspace=req.workspace)
    except KeyError as exc:
        raise HTTPException(404, "pattern not found") from exc
    db.commit()
    return PatternResponse.model_validate(store.response(item))


@router.post("/patterns/{pattern_id}/promote-namespace", response_model=PatternResponse)
def pattern_promote_namespace(pattern_id: str, target: str = Query(...), db: Session = Depends(get_db)) -> PatternResponse:
    store = PatternStore(db, settings)
    try:
        item = store.promote_namespace(pattern_id, target)
    except KeyError as exc:
        raise HTTPException(404, "pattern not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return PatternResponse.model_validate(store.response(item))


@router.post("/patterns/gc")
def pattern_gc(codebook: str | None = None, db: Session = Depends(get_db)) -> dict[str, int]:
    result = PatternStore(db, settings).garbage_collect(codebook)
    db.commit()
    return result


@router.post("/latent/pack", response_model=LatentPacket)
def latent_pack(req: LatentPackRequest) -> LatentPacket:
    return pack_latent(req.vector, req.space)


@router.post("/latent/unpack", response_model=list[float])
def latent_unpack(req: LatentUnpackRequest) -> list[float]:
    try:
        return unpack_latent(req.packet)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/negotiate", response_model=NegotiateResponse)
def negotiate(req: NegotiateRequest, db: Session = Depends(get_db)) -> NegotiateResponse:
    if req.receiver is not None:
        req.receiver = enforce_agent_scope(actor=req.receiver, workspace=req.workspace)
    else:
        enforce_agent_scope(actor=None, workspace=req.workspace)
    if SAGE_PROTOCOL not in req.capabilities.protocol_versions:
        raise HTTPException(409, f"peer must support {SAGE_PROTOCOL}")
    protocol = SAGE_PROTOCOL
    cb_name = req.codebook or settings.codebook
    principal = current_principal()
    if principal.kind == "agent" and cb_name != settings.codebook:
        raise HTTPException(403, "agent-scoped credentials may negotiate only the configured codebook")
    codebook = Codebook(db, settings)
    chain = codebook.namespace_chain(cb_name)
    missing = [c for c in codebook.all_chain(cb_name) if c.code not in req.known_codes]
    pattern_store = PatternStore(db, settings, codebook)
    missing_patterns = [
        p for p in pattern_store.list(cb_name, status="active") if p.pattern_id not in req.known_patterns
    ] if req.capabilities.supports_patterns else []
    negotiated = Capabilities(
        protocol_versions=[protocol],
        codebooks=[cb_name],
        max_packet_bytes=min(req.capabilities.max_packet_bytes, settings.max_packet_bytes),
        supports_refs=req.capabilities.supports_refs,
        supports_deltas=req.capabilities.supports_deltas,
        supports_patterns=req.capabilities.supports_patterns,
        latent_spaces=req.capabilities.latent_spaces,
        fallback_modes=req.capabilities.fallback_modes,
    )
    if req.receiver:
        KnowledgeStore(db).update_capabilities(req.receiver, negotiated.model_dump(), req.workspace)
        db.commit()
    return NegotiateResponse(
        protocol_version=protocol,
        codebook=cb_name,
        codebook_chain=chain,
        embedding_space=codebook.embedding_space,
        missing_codes=[concept_response(c, db) for c in missing[:500]],
        missing_patterns=[PatternResponse.model_validate(pattern_store.response(p)) for p in missing_patterns[:500]],
        fingerprint=codebook.fingerprint(cb_name),
        negotiated=negotiated,
    )


@router.get("/receivers/{receiver}")
def receiver_knowledge(
    receiver: str,
    workspace: str = Query(default="default"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    item = db.scalar(
        select(ReceiverKnowledge).where(
            ReceiverKnowledge.workspace == workspace,
            ReceiverKnowledge.receiver == receiver,
        )
    )
    if item is None:
        raise HTTPException(404, "receiver knowledge not found")
    return {
        "receiver": receiver,
        "workspace": workspace,
        "known_codes": KnowledgeStore(db).known_codes(receiver, workspace),
        "known_refs": KnowledgeStore(db).known_refs(receiver, workspace),
        "current_state": item.current_state,
        "capabilities": item.capabilities,
        "updated_at": item.updated_at.replace(tzinfo=item.updated_at.tzinfo or timezone.utc).isoformat(),
    }


@router.post("/facts", response_model=FactResponse)
def put_fact(req: FactPutRequest, db: Session = Depends(get_db)) -> FactResponse:
    source = enforce_agent_scope(actor=req.source, workspace=req.workspace)
    store = FactStore(db)
    item = store.put(workspace=req.workspace, subject=req.subject, predicate=req.predicate, object=req.object, epistemic_type=req.epistemic_type, source=source, confidence=req.confidence, provenance=req.provenance.model_dump() if req.provenance else {}, depends_on=req.depends_on)
    db.commit()
    return FactResponse.model_validate(store.response(item))


@router.get("/facts/{fact_id}", response_model=FactResponse)
def get_fact(fact_id: str, workspace: str = Query(default="default"), db: Session = Depends(get_db)) -> FactResponse:
    enforce_agent_scope(actor=None, workspace=workspace)
    store = FactStore(db)
    item = store.get(fact_id, workspace=workspace)
    if item is None:
        raise HTTPException(404, "fact not found")
    return FactResponse.model_validate(store.response(item))


@router.post("/facts/{fact_id}/invalidate")
def invalidate_fact(fact_id: str, req: FactInvalidateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    enforce_agent_scope(actor=None, workspace=req.workspace)
    store = FactStore(db)
    fact = store.get(fact_id, workspace=req.workspace)
    if fact is None:
        raise HTTPException(404, "fact not found")
    try:
        ids = store.invalidate(fact_id, reason=req.reason)
    except KeyError as exc:
        raise HTTPException(404, "fact not found") from exc
    db.commit()
    return {"invalidated": ids}


@router.post("/contradictions/{contradiction_id}/resolve")
def resolve_contradiction(contradiction_id: str, req: ContradictionResolveRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    enforce_agent_scope(actor=None, workspace=req.workspace)
    existing = db.get(Contradiction, contradiction_id)
    if existing is None or existing.workspace != req.workspace:
        raise HTTPException(404, "contradiction not found")
    try:
        item = FactStore(db).resolve_contradiction(contradiction_id, req.winner_fact_id, req.note)
    except KeyError as exc:
        raise HTTPException(404, "contradiction not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {"contradiction_id": item.id, "status": item.status, "resolution": item.resolution}


@router.post("/subscriptions")
def subscribe(req: SubscriptionRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    agent = enforce_agent_scope(actor=req.agent, workspace=req.workspace) or req.agent
    item = SemanticPubSub(db, settings).subscribe(workspace=req.workspace, agent=agent, concepts=req.concepts, filters=req.filters, min_confidence=req.min_confidence)
    db.commit()
    return {"subscription_id": item.id, "agent": item.agent, "concepts": item.concepts}


@router.post("/publish")
def publish(req: PublishRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    sender = enforce_agent_scope(actor=req.sender, workspace=req.workspace)
    recipients = SemanticPubSub(db, settings).publish(content=req.content, workspace=req.workspace, sender=sender, confidence=req.confidence, source_ids=req.source_ids)
    db.commit()
    return {"recipients": recipients, "count": len(recipients)}


@router.post("/routing/agents")
def register_agent_capability(req: AgentCapabilityRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = SemanticRouter(db, settings).register_agent(workspace=req.workspace, agent=req.agent, capabilities=req.capabilities, authority=req.authority, cost_score=req.cost_score, latency_ms=req.latency_ms, available=req.available, metadata=req.metadata)
    db.commit()
    return {"agent": item.agent, "capabilities": item.capabilities, "authority": item.authority, "available": item.available}


@router.post("/routing/choose")
def route_choose(req: RouteRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    sender = enforce_agent_scope(actor=req.sender, workspace=req.workspace)
    try:
        winner, score = SemanticRouter(db, settings).choose(content=req.content, workspace=req.workspace, capability=req.capability, authority=req.authority, exclude={sender} if sender else None)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"agent": winner.agent, "score": score}


@router.post("/routing/send", response_model=BusMessageResponse)
def route_send(req: RouteRequest, db: Session = Depends(get_db)) -> BusMessageResponse:
    sender = enforce_agent_scope(actor=req.sender, workspace=req.workspace)
    try:
        winner, _ = SemanticRouter(db, settings).choose(content=req.content, workspace=req.workspace, capability=req.capability, authority=req.authority, exclude={sender} if sender else None)
        item = SemanticBus(db, settings).handoff(receiver=winner.agent, content=req.content, sender=sender, act="route", workspace=req.workspace)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    db.commit()
    return bus_response(item)


@router.post("/federation/peers")
def federation_peer(req: FederationPeerRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        item = FederationStore(db, settings).register_peer(workspace=req.workspace, name=req.name, base_url=req.base_url, public_key_b64=req.public_key_b64, allowed_namespaces=req.allowed_namespaces, enabled=req.enabled)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {"peer_id": item.id, "name": item.name, "allowed_namespaces": item.allowed_namespaces}


@router.get("/federation/export/{namespace}")
def federation_export(namespace: str, source: str = Query(default="local"), db: Session = Depends(get_db)) -> dict[str, Any]:
    return FederationStore(db, settings).export_bundle(namespace, source=source)


@router.post("/federation/import")
def federation_import(req: FederationImportRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        result = FederationStore(db, settings).import_bundle(req.bundle, workspace=req.workspace)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return result


@router.post("/evals/run")
def eval_run(req: EvalRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    return run_eval(db, settings, req)



@router.post("/benchmarks/economics")
def economics_benchmark(req: EconomicsBenchmarkRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Measure model-token/cost economics across raw, JSON, refs, SAGE, and supplied RAG/summary baselines."""
    try:
        return run_sage_economics_benchmark(db, settings, req)
    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/benchmarks/economics/observed")
def economics_observed(req: ObservedEconomicsRequest) -> dict[str, Any]:
    """Score actual recorded provider usage as cost per successful task."""
    return score_observed_runs([row.model_dump(exclude_none=True) for row in req.observations], req.price.model_dump())


@router.post("/native-token-gate", response_model=NativeTokenGateResponse)
def native_token_gate(req: NativeTokenGateRequest) -> NativeTokenGateResponse:
    allowed = req.eval_score >= settings.native_token_min_eval_score
    return NativeTokenGateResponse(
        allowed=allowed,
        required_score=settings.native_token_min_eval_score,
        reason=(
            "semantic fidelity threshold met; native-token experimentation may proceed behind a feature flag"
            if allowed
            else "native semantic tokens are intentionally gated until eval fidelity meets the configured threshold"
        ),
    )


@router.post("/maintenance/cleanup")
def maintenance_cleanup(db: Session = Depends(get_db)) -> dict[str, int]:
    return cleanup(db, settings)


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, bool]:
    db.execute(text("SELECT 1"))
    return {"ready": True}
