import json

from creator.api.responses import success_response


def test_success_response_preserves_repeated_headers_and_request_id() -> None:
    response = success_response(
        {"ready": True},
        headers=[
            ("Set-Cookie", "creator_access=access; HttpOnly"),
            ("Set-Cookie", "creator_refresh=refresh; HttpOnly"),
            ("X-Request-ID", "must-not-replace-generated-id"),
        ],
    )

    set_cookie = response.headers.getlist("set-cookie")
    assert set_cookie == [
        "creator_access=access; HttpOnly",
        "creator_refresh=refresh; HttpOnly",
    ]
    body = json.loads(response.body)
    assert response.headers["x-request-id"] == body["meta"]["request_id"]
