"""Validated configuration models for r0env."""
from __future__ import annotations
import os
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

class ResolutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_ip: str | None = None
    sources: list[str] = Field(default_factory=lambda: ["maxmind-local", "secondary-api"])
    min_confidence: float = Field(0.85, ge=0, le=1)
    on_conflict: Literal["require_approval", "reject", "first"] = "require_approval"

class EgressConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["direct", "http", "https", "socks5"] = "direct"
    endpoint: str | None = None
    username: SecretStr | None = None
    password: SecretStr | None = None
    expected_asn: list[str] = Field(default_factory=list)
    ipv6: Literal["allow", "block", "proxy"] = "block"
    kill_switch: bool = True

    @field_validator("endpoint")
    @classmethod
    def endpoint_required_for_proxy(cls, value, info):
        if info.data.get("mode") != "direct" and not value:
            raise ValueError("endpoint is required when egress mode is not direct")
        return value

class DNSConfig(BaseModel):
    mode: Literal["system", "udp", "dot", "doh"] = "system"
    servers: list[str] = Field(default_factory=list)
    fallback: Literal["allow", "deny"] = "deny"

class WebRTCConfig(BaseModel):
    ip_handling: Literal["default", "proxy_only"] = "proxy_only"
    allow_udp: bool = False
    stun_servers: list[str] = Field(default_factory=list)

class BrowserConfig(BaseModel):
    engine: Literal["chromium", "firefox", "webkit"] = "chromium"
    version: str = "pinned"
    user_agent: str | None = None
    locale: str | None = None
    timezone_id: str | None = None
    viewport: dict[str, int | float] = Field(default_factory=dict)
    languages: list[str] = Field(default_factory=list)
    webrtc: WebRTCConfig = Field(default_factory=WebRTCConfig)
    canvas_webgl: dict[str, str | bool] = Field(default_factory=lambda: {"mode": "deterministic-test-profile", "hardware_acceleration": False})

class OSConfig(BaseModel):
    timezone: str | None = None
    locale: str | None = None
    keyboard_layout: str | None = None

class InspectionConfig(BaseModel):
    interval_seconds: int = Field(300, ge=1)
    timeout_seconds: int = Field(20, ge=1)
    auto_correct: list[Literal["dns", "egress", "webrtc", "browser_context", "os_locale"]] = Field(default_factory=lambda: ["dns", "egress", "webrtc", "browser_context", "os_locale"])
    alert_only: list[str] = Field(default_factory=list)
    consecutive_failures: int = Field(2, ge=1)
    probes: list[str] = Field(default_factory=lambda: ["egress", "dns", "webrtc", "browser", "os"])

class TargetConfig(BaseModel):
    type: Literal["host", "container", "vm"] = "host"
    id: str = "local"

class R0EnvConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = "v1"
    case_id: str
    target: TargetConfig = Field(default_factory=TargetConfig)
    authorization: dict = Field(default_factory=dict)
    resolution: ResolutionConfig = Field(default_factory=ResolutionConfig)
    region: dict = Field(default_factory=dict)
    network: dict = Field(default_factory=dict)
    egress: EgressConfig = Field(default_factory=EgressConfig)
    dns: DNSConfig = Field(default_factory=DNSConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    os: OSConfig = Field(default_factory=OSConfig)
    inspection: InspectionConfig = Field(default_factory=InspectionConfig)
    rollback: dict = Field(default_factory=dict)
    audit: dict = Field(default_factory=dict)

    @property
    def auto_apply(self) -> bool:
        return os.environ.get("R0ENV_AUTO_APPLY") == "1"

    def require_confirmation(self, confirmed: bool = False) -> None:
        if not (confirmed or self.auto_apply):
            raise PermissionError("apply requires --confirm or R0ENV_AUTO_APPLY=1")

def load_config(data: dict) -> R0EnvConfig:
    return R0EnvConfig.model_validate(data)
