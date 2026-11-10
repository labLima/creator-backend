"""The legacy ``planning`` table was removed by T13.

Planning is persisted in ``content_plans`` and its satellites; this module is
kept so the capability package keeps its structural vocabulary.
"""

from __future__ import annotations

from creator.infrastructure.database.types import timestamp_tz

timestamp = timestamp_tz
