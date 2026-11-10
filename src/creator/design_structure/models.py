"""The legacy ``design_structure`` table was removed by T13.

Designs live in ``post_designs`` and ``design_slides``; this module is kept so
the capability package keeps its structural vocabulary.
"""

from __future__ import annotations

from creator.infrastructure.database.types import timestamp_tz

timestamp = timestamp_tz
