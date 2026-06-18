"""Runtime helpers for OpenCode integrations."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping

DEFAULT_API_URL = "https://api.openai.com"


def proxy_base_url(port: int) -> str:
    """Return the local proxy base URL used by OpenCode-compatible integrations."""
    return f"http://127.0.0.1:{port}/v1"


# Headroom-managed JSON marker comments for idempotent block injection.
_PROVIDER_MARKER_START = "// --- Headroom proxy provider ---"
_PROVIDER_MARKER_END = "// --- end Headroom proxy provider ---"
_MCP_MARKER_START = "// --- Headroom MCP server ---"
_MCP_MARKER_END = "// --- end Headroom MCP server ---"


_DEFAULT_MODELS = {
    "claude-sonnet-4-6": {
        "name": "Claude Sonnet 4.6",
        "limit": {"context": 200000, "output": 16384},
    },
    "claude-opus-4-6": {
        "name": "Claude Opus 4.6",
        "limit": {"context": 200000, "output": 16384},
    },
    "claude-haiku-4-5-20251001": {
        "name": "Claude Haiku 4.5",
        "limit": {"context": 200000, "output": 8192},
    },
    "gpt-4o": {
        "name": "GPT-4o",
        "limit": {"context": 128000, "output": 16384},
    },
    "gpt-4.1": {
        "name": "GPT-4.1",
        "limit": {"context": 1048576, "output": 32768},
    },
}


_DEFAULT_CONFIG = {
    "provider": {
        "headroom": {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Headroom Proxy",
            "options": {"baseURL": None},  # filled at runtime
            "models": _DEFAULT_MODELS,
        }
    },
    "model": "headroom/claude-sonnet-4-6",
}


def _build_mcp_block(port: int) -> dict[str, object]:
    """Build the MCP server block for OpenCode config."""
    return {
        "mcp": {
            "headroom": {
                "type": "remote",
                "url": f"http://127.0.0.1:{port}/mcp",
                "enabled": True,
            }
        }
    }


def build_opencode_config_content(
    *,
    port: int,
    model: str = "headroom/claude-sonnet-4-6",
    include_mcp: bool = True,
) -> dict[str, object]:
    """Build the JSON payload for ``OPENCODE_CONFIG_CONTENT``.

    This dict merges with the user's existing opencode.json, overriding
    model selection and adding the headroom provider.
    """
    config = {
        "provider": {
            "headroom": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Headroom Proxy",
                "options": {"baseURL": proxy_base_url(port)},
                "models": _DEFAULT_MODELS,
            }
        },
        "model": model,
    }
    if include_mcp:
        config["mcp"] = {
            "headroom": {
                "type": "remote",
                "url": f"http://127.0.0.1:{port}/mcp",
                "enabled": True,
            }
        }
    return config


def build_launch_env(
    port: int,
    environ: Mapping[str, str] | None = None,
    project: str | None = None,
    *,
    model: str = "headroom/claude-sonnet-4-6",
    include_mcp: bool = True,
) -> tuple[dict[str, str], list[str]]:
    """Build environment variables for OpenCode through the local proxy.

    Sets ``OPENCODE_CONFIG_CONTENT`` with the headroom provider definition.
    Also sets ``OPENAI_BASE_URL`` and ``ANTHROPIC_BASE_URL`` as fallbacks.
    """
    env = dict(environ or os.environ)
    base_url = proxy_base_url(port)

    config_content = build_opencode_config_content(
        port=port,
        model=model,
        include_mcp=include_mcp,
    )
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config_content, separators=(",", ":"))

    # Fallback env vars for OpenCode versions that respect them.
    env["OPENAI_BASE_URL"] = base_url
    env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"

    env_vars_display = [
        f"OPENCODE_CONFIG_CONTENT={{provider: headroom, model: {model}}}",
        f"OPENAI_BASE_URL={base_url}",
        f"ANTHROPIC_BASE_URL=http://127.0.0.1:{port}",
    ]

    # Per-project savings attribution (same pattern as codex).
    if project and "HEADROOM_PROJECT" not in env:
        env["HEADROOM_PROJECT"] = project

    return env, env_vars_display
