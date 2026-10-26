from __future__ import annotations

from enum import StrEnum

from creator.domain.exceptions import DomainError


class AgentKickoffErrorCode(StrEnum):
    INPUT_INVALID = "AGENT_INPUT_INVALID"
    WORKSPACE_UNAUTHORIZED = "WORKSPACE_UNAUTHORIZED"
    ROLE_UNSUPPORTED = "AGENT_ROLE_UNSUPPORTED"
    OUTPUT_MALFORMED = "AGENT_OUTPUT_MALFORMED"
    OUTPUT_SCHEMA_INVALID = "AGENT_OUTPUT_SCHEMA_INVALID"
    PROVIDER_FAILURE = "AGENT_PROVIDER_FAILURE"
    PROVIDER_UNAVAILABLE = "AGENT_PROVIDER_UNAVAILABLE"


class AgentKickoffError(DomainError):
    """A safe, bounded failure from the typed agent provider boundary."""

    def __init__(self, code: AgentKickoffErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
