"""Pure configuration and diagnostic helpers for Background CPU Governor."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

DEFAULT_CONFIG: dict[str, bool] = {
    "enabled": True,
    "pause_on_app_deactivate": True,
    "pause_css_animations": True,
    "pause_raf": True,
    "warn_software_driver": True,
}

_SOFTWARE_FLAG_MARKERS = ("--disable-gpu", "--disable-gpu-compositing")


def normalize_config(raw: Mapping[str, Any] | None) -> dict[str, bool]:
    """Return a full boolean config dictionary with defaults for missing keys."""
    result = dict(DEFAULT_CONFIG)
    if not isinstance(raw, Mapping):
        return result
    for key, default in DEFAULT_CONFIG.items():
        val = raw.get(key)
        if isinstance(val, bool):
            result[key] = val
        elif val is not None:
            result[key] = bool(val)
        else:
            result[key] = default
    return result


def to_js_config(config: Mapping[str, Any]) -> dict[str, bool]:
    """Convert addon config to the camelCase object consumed by web/governor.js."""
    normalized = normalize_config(config)
    return {
        "enabled": normalized["enabled"],
        "pauseCssAnimations": normalized["pause_css_animations"],
        "pauseRaf": normalized["pause_raf"],
    }


def build_config_script(config: Mapping[str, Any]) -> str:
    """Return JS initializing window.__ankiCpuGovernorConfig."""
    payload = json.dumps(to_js_config(config), sort_keys=True)
    return f"window.__ankiCpuGovernorConfig = {payload};"


def build_set_paused_script(paused: bool) -> str:
    """Return JS toggling background pause state on an initialized WebView."""
    literal = "true" if paused else "false"
    return f"window.__ankiCpuGovernor && window.__ankiCpuGovernor.setPaused({literal});"


def build_set_enabled_script(enabled: bool) -> str:
    """Return JS enabling or disabling the governor inside an initialized WebView."""
    literal = "true" if enabled else "false"
    return f"window.__ankiCpuGovernor && window.__ankiCpuGovernor.setEnabled({literal});"


def detect_software_compositing(environ: Mapping[str, str], qt_flags: str = "") -> bool:
    """True when environment variables or Chromium flags force software rendering."""
    combined_flags = " ".join(
        part
        for part in (
            environ.get("QTWEBENGINE_CHROMIUM_FLAGS", ""),
            qt_flags,
        )
        if part
    )
    if any(marker in combined_flags for marker in _SOFTWARE_FLAG_MARKERS):
        return True
    if environ.get("ANKI_VIDEO_DRIVER", "").strip().lower() == "software":
        return True
    if environ.get("QT_OPENGL", "").strip().lower() == "software":
        return True
    return environ.get("QT_QUICK_BACKEND", "").strip().lower() == "software"


def format_status_report(
    enabled: bool,
    paused: bool,
    webview_count: int,
    software_compositing: bool,
) -> str:
    """Format a concise status summary for Tools -> Background CPU Governor -> Show Status."""
    lines = [
        f"Throttling: {'Enabled' if enabled else 'Disabled'}",
        f"Current State: {'Paused (background)' if paused else 'Active (focused)'}",
        f"Governed WebViews: {webview_count}",
        (
            "WebEngine Compositing: Software (--disable-gpu-compositing / software driver detected). "
            "Hardware video driver in Preferences -> Appearance reduces WebView CPU further."
            if software_compositing
            else "WebEngine Compositing: Hardware / Default"
        ),
    ]
    return "\n".join(lines)
