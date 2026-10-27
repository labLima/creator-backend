# Creator JWT vendor notice

This directory is the Creator-owned infrastructure boundary for the patched
`fastapi-jwt-auth` compatibility surface.

- Upstream baseline: `fastapi-jwt-auth` 0.5.0
- Upstream license: MIT
- Source: https://github.com/IndominusByte/fastapi-jwt-auth
- Creator changes: Pydantic 2/PyJWT 2 compatibility and a narrow encode/decode
  surface used only by `creator.infrastructure.auth`.

The application and domain layers depend on Creator ports, never on this vendor
surface or on PyJWT directly. Updates must record the upstream revision, patch
diff, license review, and security review in ADR-022 before being merged.
