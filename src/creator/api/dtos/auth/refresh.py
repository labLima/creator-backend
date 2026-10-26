from pydantic import Field

from creator.api.dtos.base import CreatorDTO


class AuthRefreshRequest(CreatorDTO):
    refresh_token: str = Field(min_length=1, max_length=4096, repr=False)
