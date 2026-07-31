from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAGE_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./sage.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    api_keys: list[str] = Field(default_factory=list)
    agent_keys: dict[str, str] = Field(default_factory=dict)
    auth_required: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    docs_enabled: bool = True
    metrics_public: bool = False
    http_max_body_bytes: int = 52_428_800
    max_inline_bytes: int = 2048
    max_input_bytes: int = 50_000_000
    max_store_bytes: int = 50_000_000
    max_packet_bytes: int = 8192
    default_token_budget: int = 1200
    chars_per_token_estimate: float = 4.0
    semantic_threshold: float = 0.93
    semantic_lossless_threshold: float = 0.985
    promotion_min_count: int = 8
    promotion_min_savings_bytes: int = 64
    promotion_max_neighbor_similarity: float = 0.88
    pattern_learning_enabled: bool = True
    pattern_string_constants_enabled: bool = False
    pattern_min_components: int = 2
    pattern_max_components: int = 6
    pattern_max_observations_per_message: int = 64
    pattern_candidate_min_count: int = 4
    pattern_min_savings_bytes: int = 64
    pattern_shadow_min_samples: int = 3
    pattern_shadow_min_success: float = 0.95
    pattern_auto_activate: bool = True
    pattern_candidate_retention_days: int = 30
    semantic_firewall_enabled: bool = True
    critical_semantic_threshold: float = 0.999
    pattern_recursive_learning_enabled: bool = True
    pattern_utility_min_score: float = 0.5
    pattern_counterfactual_required: bool = True
    pattern_counterfactual_min_samples: int = 3
    pattern_counterfactual_min_fidelity: float = 0.99
    pattern_receiver_min_fidelity: float = 0.95
    pattern_gc_cooling_days: int = 30
    pattern_gc_retire_days: int = 90
    pattern_namespace_promotion_min_utility: float = 0.95
    codebook: str = "global"
    core_codebook: str = "core"
    max_message_atoms: int = 256
    auto_create_schema: bool = True
    embedding_provider: Literal["hash", "openai", "openai_compatible"] = "hash"
    embedding_api_url: str = ""
    embedding_api_key: SecretStr | None = None
    embedding_model: str = ""
    embedding_timeout_seconds: float = 10.0
    ref_encryption_key: SecretStr | None = None
    require_ref_encryption: bool = False
    default_ref_ttl_seconds: int | None = None
    semantic_cache_enabled: bool = True
    semantic_cache_ttl_seconds: int = 3600
    bus_claim_lease_seconds: int = 60
    default_bus_ttl_seconds: int | None = None
    audit_retention_days: int = 30
    native_token_min_eval_score: float = 0.98
    benchmark_tokenizer_api_key: SecretStr | None = None
    benchmark_tokenizer_allowed_hosts: list[str] = Field(default_factory=list)
    packet_signing_private_key: SecretStr | None = None
    packet_signing_public_key: SecretStr | None = None
    packet_signing_key_id: str = "default"
    require_packet_signatures: bool = False
    otel_enabled: bool = False
    otel_service_name: str = "sage"
    federation_timeout_seconds: float = 10.0
    routing_cost_weight: float = 1.0
    routing_latency_weight: float = 0.001
    routing_knowledge_weight: float = 2.0

    @field_validator("api_keys", mode="before")
    @classmethod
    def split_api_keys(cls, value: object) -> object:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @field_validator("allowed_hosts", "benchmark_tokenizer_allowed_hosts", mode="before")
    @classmethod
    def split_string_lists(cls, value: object) -> object:
        if isinstance(value, str):
            return [v.strip().lower() for v in value.split(",") if v.strip()]
        return value

    @field_validator("semantic_threshold", "semantic_lossless_threshold", "promotion_max_neighbor_similarity", "native_token_min_eval_score", "pattern_shadow_min_success", "critical_semantic_threshold", "pattern_counterfactual_min_fidelity", "pattern_receiver_min_fidelity", "pattern_namespace_promotion_min_utility")
    @classmethod
    def validate_ratio(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("ratio setting must be in [0, 1]")
        return value

    @field_validator("chars_per_token_estimate")
    @classmethod
    def validate_chars_per_token(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("chars_per_token_estimate must be > 0")
        return value

    @field_validator("max_inline_bytes", "max_input_bytes", "max_store_bytes", "max_packet_bytes", "default_token_budget", "http_max_body_bytes", "semantic_cache_ttl_seconds", "bus_claim_lease_seconds", "audit_retention_days", "db_pool_size", "db_pool_timeout_seconds", "db_pool_recycle_seconds")
    @classmethod
    def validate_positive_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("size, budget, lease, and retention settings must be positive")
        return value

    @field_validator("db_max_overflow")
    @classmethod
    def validate_nonnegative_integer(cls, value: int) -> int:
        if value < 0:
            raise ValueError("db_max_overflow must be nonnegative")
        return value

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.pattern_min_components < 2:
            raise ValueError("pattern_min_components must be >= 2")
        if self.pattern_max_components < self.pattern_min_components:
            raise ValueError("pattern_max_components must be >= pattern_min_components")
        if self.pattern_max_observations_per_message < 1:
            raise ValueError("pattern_max_observations_per_message must be >= 1")
        if self.pattern_candidate_min_count < 1 or self.pattern_shadow_min_samples < 1:
            raise ValueError("pattern count thresholds must be >= 1")
        if self.pattern_min_savings_bytes < 0:
            raise ValueError("pattern_min_savings_bytes must be >= 0")
        if self.pattern_candidate_retention_days < 1:
            raise ValueError("pattern_candidate_retention_days must be >= 1")
        if self.pattern_counterfactual_min_samples < 1:
            raise ValueError("pattern_counterfactual_min_samples must be >= 1")
        if self.pattern_gc_cooling_days < 1 or self.pattern_gc_retire_days < self.pattern_gc_cooling_days:
            raise ValueError("pattern GC thresholds are invalid")
        if self.auth_required:
            if not self.api_keys:
                raise ValueError("at least one service api_key must be configured when auth_required=true")
            if any(len(key) < 32 for key in self.api_keys):
                raise ValueError("each service API key must be at least 32 characters")
            if any(len(key) < 32 for key in self.agent_keys):
                raise ValueError("each agent API key must be at least 32 characters")
            if set(self.api_keys) & set(self.agent_keys):
                raise ValueError("service and agent API keys must be distinct")
            for scope in self.agent_keys.values():
                if not scope or scope.startswith(":") or scope.endswith(":"):
                    raise ValueError("agent key scope must be 'workspace:agent' or 'agent'")
        if self.env.lower() == "production":
            if not self.auth_required:
                raise ValueError("production requires auth_required=true")
            if self.auto_create_schema:
                raise ValueError("production requires auto_create_schema=false and managed migrations")
            if self.database_url.startswith("sqlite"):
                raise ValueError("production requires a server database")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("production requires explicit allowed_hosts")
            if self.docs_enabled:
                raise ValueError("production requires docs_enabled=false")
            if self.embedding_provider.lower() in {"openai", "openai_compatible"} and not self.embedding_api_url.lower().startswith("https://"):
                raise ValueError("production learned embedding endpoints must use https")
        if self.require_packet_signatures and self.packet_signing_public_key is None:
            raise ValueError("packet_signing_public_key is required when require_packet_signatures=true")
        for label, secret in (("packet_signing_private_key", self.packet_signing_private_key), ("packet_signing_public_key", self.packet_signing_public_key)):
            if secret is not None:
                try:
                    raw = base64.urlsafe_b64decode(secret.get_secret_value() + "=" * (-len(secret.get_secret_value()) % 4))
                except Exception as exc:
                    raise ValueError(f"{label} must be urlsafe-base64") from exc
                if len(raw) != 32:
                    raise ValueError(f"{label} must decode to exactly 32 bytes")
        if self.require_ref_encryption and self.ref_encryption_key is None:
            raise ValueError("ref_encryption_key is required when require_ref_encryption=true")
        if self.ref_encryption_key is not None:
            try:
                key = base64.urlsafe_b64decode(self.ref_encryption_key.get_secret_value().encode())
            except Exception as exc:
                raise ValueError("ref_encryption_key must be urlsafe-base64") from exc
            if len(key) != 32:
                raise ValueError("ref_encryption_key must decode to exactly 32 bytes")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
