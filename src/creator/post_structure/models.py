"""The legacy ``post_structure`` table was removed by T13.

Posts live in ``posts``/``captions``/``post_designs``/``design_slides``; this
module is kept so the capability package keeps its structural vocabulary.
"""

from __future__ import annotations

from creator.infrastructure.database.types import timestamp_tz

timestamp = timestamp_tz
