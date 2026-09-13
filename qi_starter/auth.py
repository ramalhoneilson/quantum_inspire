"""Authentication and credential management for Quantum Inspire."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG_PATH = "~/.quantuminspire/config.json"


def check_auth_status(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Inspect the Quantum Inspire credentials file offline.

    Quantum Inspire stores OAuth tokens locally in `~/.quantuminspire/config.json`
    after `qi login` is executed. This function performs a lightweight check
    without initiating any network requests or importing the heavy SDK.

    Args:
        config_path: Path to the Quantum Inspire configuration file.

    Returns:
        A dictionary containing:
            - present: bool, whether the config file exists
            - path: str, expanded path to the file
            - host: str or None, default hostname configured
            - refresh_expires_at: str, ISO 8601 expiry timestamp of refresh token (or "")
            - is_expired: bool or None, whether refresh token has expired
    """
    expanded_path = os.path.expanduser(config_path)
    info: Dict[str, Any] = {
        "present": False,
        "path": expanded_path,
        "host": None,
        "refresh_expires_at": "",
        "is_expired": None,
    }

    if not os.path.exists(expanded_path):
        return info

    try:
        with open(expanded_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        info["present"] = True
        host = doc.get("default_host")
        info["host"] = host

        tokens = ((doc.get("auths") or {}).get(host) or {}).get("tokens") or {}
        generated_at = tokens.get("generated_at")
        refresh_in = tokens.get("refresh_expires_in")

        if generated_at is not None and refresh_in is not None:
            expires_timestamp = float(generated_at) + float(refresh_in)
            expiry_dt = datetime.datetime.fromtimestamp(
                expires_timestamp, tz=datetime.timezone.utc
            )
            info["refresh_expires_at"] = expiry_dt.isoformat()
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            info["is_expired"] = now_dt >= expiry_dt
    except (OSError, ValueError, TypeError, KeyError) as err:
        info["error"] = str(err)

    return info


def get_provider():
    """Instantiate QIProvider, translating auth failures into beginner-friendly advice.

    Returns:
        QIProvider: An authenticated instance of Qiskit's Quantum Inspire provider.

    Raises:
        RuntimeError: If authentication is missing, expired, or dependencies are not installed.
    """
    try:
        from qiskit_quantuminspire.qi_provider import QIProvider
    except ImportError as exc:
        raise RuntimeError(
            "qiskit-quantuminspire is not installed in the active environment.\n"
            "Install it via:\n"
            "    pip install qiskit-quantuminspire quantuminspire\n"
            "or with uv:\n"
            "    uv add qiskit-quantuminspire quantuminspire"
        ) from exc

    status = check_auth_status()
    if not status["present"]:
        raise RuntimeError(
            "No Quantum Inspire credentials found at ~/.quantuminspire/config.json.\n"
            "To log in, run the official Quantum Inspire CLI login command:\n"
            "    qi login\n"
            "This will open a browser window for OAuth authentication."
        )

    if status.get("is_expired"):
        raise RuntimeError(
            f"Quantum Inspire refresh token expired at {status['refresh_expires_at']}.\n"
            "Please re-authenticate by running:\n"
            "    qi login --force"
        )

    try:
        return QIProvider()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to connect to Quantum Inspire as an authenticated user: {exc}\n"
            "Try re-authenticating with: qi login --force"
        ) from exc
