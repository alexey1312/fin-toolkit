"""Serialize MCP tool responses to JSON or TOON format."""

from __future__ import annotations

import json
from typing import Any

from toon_format import encode as toon_encode


def serialize(data: dict[str, Any], fmt: str = "toon") -> str:
    """Serialize *data* dict to the requested format.

    Args:
        data: Payload to serialize.
        fmt: ``"toon"`` (default, token-efficient) or ``"json"``.

    Returns:
        Encoded string.

    Raises:
        ValueError: If *fmt* is not ``"toon"`` or ``"json"``.
    """
    if fmt == "json":
        return json.dumps(data)
    if fmt == "toon":
        return toon_encode(data)
    msg = f"Unsupported format: {fmt!r}. Use 'toon' or 'json'."
    raise ValueError(msg)
