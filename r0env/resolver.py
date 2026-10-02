"""GeoIP resolution with reserved-address rejection and conflict policy."""
from __future__ import annotations
import ipaddress, json, urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable

class ResolutionError(ValueError): pass
class PrivateAddressError(ResolutionError): pass
class SourceConflictError(ResolutionError): pass

@dataclass(frozen=True)
class GeoResult:
    ip: str
    country_code: str | None = None
    country: str | None = None
    region: str | None = None
    timezone: str | None = None
    asn: str | None = None
    source: str = "unknown"
    confidence: float = 0.0

def validate_public_ip(value: str) -> str:
    try: addr = ipaddress.ip_address(value)
    except ValueError as e: raise ResolutionError(f"invalid IP: {value}") from e
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast or addr.is_unspecified:
        raise PrivateAddressError(f"private/reserved IP is not eligible for automatic resolution: {value}")
    return str(addr)

class Resolver:
    def __init__(self, providers: Iterable[Callable[[str], GeoResult]], on_conflict: str = "require_approval"):
        self.providers, self.on_conflict = list(providers), on_conflict

    def resolve(self, ip: str) -> GeoResult:
        public_ip = validate_public_ip(ip)
        results = []
        failures = []
        for provider in self.providers:
            try:
                result = provider(public_ip)
                if result is not None:
                    results.append(result)
            except Exception as exc:
                failures.append(str(exc))
        if not results:
            raise ResolutionError("all GeoIP sources failed: " + "; ".join(failures))
        keys = {(r.country_code, r.timezone) for r in results}
        if len(keys) > 1 and self.on_conflict in {"require_approval", "reject"}:
            raise SourceConflictError(f"GeoIP sources disagree: {sorted(keys)}")
        best = max(results, key=lambda r: r.confidence)
        return best

def ipwho_provider(ip: str) -> GeoResult:
    req = urllib.request.Request(f"https://ipwho.is/{ip}", headers={"User-Agent": "r0env/0.1"})
    with urllib.request.urlopen(req, timeout=8) as response: data = json.load(response)
    if data.get("success") is False: raise ResolutionError(data.get("message", "lookup failed"))
    tz = data.get("timezone") or {}; conn = data.get("connection") or {}
    return GeoResult(ip=ip, country_code=data.get("country_code"), country=data.get("country"), region=data.get("region"), timezone=tz.get("id") if isinstance(tz, dict) else tz, asn=conn.get("asn"), source="ipwho.is", confidence=0.8)
