"""Request payloads for the credit capability.

The Credit Transaction ledger is append-only and read-only through HTTP
(ADR-019), so the capability publishes no write payload. The module stays in
place because `creator.credit` is a capability boundary, not a single file.
"""

from __future__ import annotations

__all__: list[str] = []
