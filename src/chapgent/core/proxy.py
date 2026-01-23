"""LiteLLM proxy configuration and startup utilities.

Shared between CLI commands and TUI for proxy management.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 4000


def generate_litellm_config() -> dict[str, Any]:
    """Generate LiteLLM proxy configuration.

    Returns:
        Configuration dict ready for YAML serialization.
    """
    return {
        "model_list": [
            {
                "model_name": "anthropic-claude",
                "litellm_params": {"model": "anthropic/claude-sonnet-4-20250514"},
            },
            {
                "model_name": "claude-sonnet-4-20250514",
                "litellm_params": {"model": "anthropic/claude-sonnet-4-20250514"},
            },
            {
                "model_name": "claude-3-5-haiku-20241022",
                "litellm_params": {"model": "anthropic/claude-3-5-haiku-20241022"},
            },
        ],
        "general_settings": {"forward_client_headers_to_llm_api": True},
        "litellm_settings": {"drop_params": True},
    }


def find_litellm_binary() -> str | None:
    """Find the litellm CLI binary.

    Checks venv first, then system PATH.

    Returns:
        Path to litellm binary, or None if not found.
    """
    # Check venv first
    venv_litellm = Path(sys.executable).parent / "litellm"
    if venv_litellm.exists():
        return str(venv_litellm)

    # Fall back to system PATH
    return shutil.which("litellm")


def write_proxy_config(config: dict[str, Any] | None = None) -> Path:
    """Write LiteLLM config to temp file.

    Args:
        config: Config dict, or None to use default.

    Returns:
        Path to the written config file.
    """
    if config is None:
        config = generate_litellm_config()

    config_dir = Path(tempfile.gettempdir()) / "chapgent"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "litellm-proxy.yaml"

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


def is_proxy_running(host: str = DEFAULT_PROXY_HOST, port: int = DEFAULT_PROXY_PORT) -> bool:
    """Check if proxy is already running by trying to connect.

    Args:
        host: Proxy host address.
        port: Proxy port number.

    Returns:
        True if proxy is accepting connections.
    """
    import socket

    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def start_proxy_background(
    host: str = DEFAULT_PROXY_HOST,
    port: int = DEFAULT_PROXY_PORT,
    timeout: float = 10.0,
) -> bool:
    """Start the LiteLLM proxy in the background.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        timeout: Max seconds to wait for proxy to start.

    Returns:
        True if proxy started successfully, False otherwise.
    """
    litellm_cmd = find_litellm_binary()
    if not litellm_cmd:
        return False

    config_path = write_proxy_config()

    # LiteLLM requires ANTHROPIC_API_KEY env var even when using OAuth via proxy.
    # The actual auth comes from the forwarded Authorization header, but the proxy
    # needs this env var to initialize. We use a placeholder value.
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = env.get("ANTHROPIC_API_KEY", "placeholder-for-oauth-proxy")

    try:
        subprocess.Popen(
            [litellm_cmd, "--config", str(config_path), "--host", host, "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent process
            env=env,
        )
    except FileNotFoundError:
        return False

    # Wait for proxy to be ready
    iterations = int(timeout / 0.5)
    for _ in range(iterations):
        time.sleep(0.5)
        if is_proxy_running(host, port):
            return True

    return False


__all__ = [
    "DEFAULT_PROXY_HOST",
    "DEFAULT_PROXY_PORT",
    "generate_litellm_config",
    "find_litellm_binary",
    "write_proxy_config",
    "is_proxy_running",
    "start_proxy_background",
]
