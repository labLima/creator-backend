# Migração do SPA para autenticação por cookies

Use `credentials: "include"` em todas as chamadas à API. O backend define
`creator_access` e `creator_refresh` como `HttpOnly`; JavaScript não deve tentar
ler esses cookies nem usar `localStorage` para guardar tokens.

O cookie `creator_csrf` é legível pelo SPA. Envie seu valor em
`X-CSRF-Token` para toda requisição `POST`, `PUT`, `PATCH` ou `DELETE`. Se o
cookie CSRF não estiver disponível, chame `GET /api/v1/auth/csrf` após
restaurar a sessão.

Implemente refresh single-flight: a primeira requisição que receber `401`
inicia `POST /api/v1/auth/refresh`; requisições concorrentes aguardam a mesma
Promise e não iniciam outra rotação. O refresh não recebe corpo no contrato
final. `409 REFRESH_IN_PROGRESS` significa que outra aba já venceu a rotação;
aguarde e tente novamente. Depois de um `401` de refresh, descarte o estado da
aplicação e encaminhe o Principal para login.

Durante uma release de transição, login e signup podem retornar tokens no JSON
para clientes antigos. O cliente novo deve ignorar esses campos. No cutover,
`AUTH_LEGACY_BEARER_ENABLED=false` e `AUTH_TOKEN_BODY_ENABLED=false`; apenas
cookies permanecem no contrato.
