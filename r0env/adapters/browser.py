"""Browser profile adapter: 同时支持 Firefox 和 Chromium。"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrowserProfile:
    user_agent: str = ""
    locale: str = "en-US"
    timezone_id: str = "UTC"
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 720})
    device_scale_factor: int = 1
    color_scheme: str = "light"
    engine: str = "firefox"          # firefox | chromium


class BrowserAdapter:
    def discover(self, target: Any = None) -> dict:
        return {"engine": "firefox", "installed": True}

    def plan(self, observed: Any, desired: BrowserProfile) -> dict:
        engine = (getattr(desired, "engine", None) or "firefox").lower()
        if engine == "firefox":
            return self._plan_firefox(desired)
        return self._plan_chromium(desired)

    def apply(self, plan: dict, dry_run: bool = True) -> dict:
        if dry_run:
            return {"applied": False, "dry_run": True, "diff": plan}
        return {"applied": True, "dry_run": False, "diff": plan}

    def verify(self, desired: BrowserProfile, target: Any = None) -> dict:
        return {"verified": True}

    def rollback(self, snapshot: Any, target: Any = None) -> dict:
        return {"rolled_back": True}

    # ---------- Firefox ----------
    def _plan_firefox(self, p: BrowserProfile) -> dict:
        return {
            "engine": "firefox",
            "firefox_prefs": self._firefox_prefs(p),
            "context_options": self._firefox_context(p),
        }

    def _firefox_prefs(self, p: BrowserProfile) -> dict:
        return {
            "intl.accept_languages": p.locale,
            "general.useragent.override": p.user_agent or "Mozilla/5.0",
            "privacy.resistFingerprinting": False,
            "privacy.trackingprotection.enabled": False,
            "media.navigator.enabled": False,
            "media.peerconnection.enabled": False,
            "network.proxy.type": 0,
        }

    def _firefox_context(self, p: BrowserProfile) -> dict:
        return {
            "locale": p.locale,
            "timezone_id": p.timezone_id,
            "viewport": p.viewport,
            "device_scale_factor": p.device_scale_factor,
            "color_scheme": p.color_scheme,
        }

    # ---------- Chromium ----------
    def _plan_chromium(self, p: BrowserProfile) -> dict:
        return {
            "engine": "chromium",
            "chromium_args": self._chromium_args(p),
            "context_options": self._chromium_context(p),
        }

    def _chromium_args(self, p: BrowserProfile) -> list:
        return [
            "--force-webrtc-ip-handling-policy=proxy_only",
            "--webrtc-stun-probe-trial=Disabled",
            f"--lang={p.locale}",
        ]

    def _chromium_context(self, p: BrowserProfile) -> dict:
        return {
            "user_agent": p.user_agent or "Mozilla/5.0",
            "locale": p.locale,
            "timezone_id": p.timezone_id,
            "viewport": p.viewport,
            "device_scale_factor": p.device_scale_factor,
            "color_scheme": p.color_scheme,
        }
