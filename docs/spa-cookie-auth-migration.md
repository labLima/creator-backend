# Migração do SPA para autenticação por cookies

Use `credentials: "include"` em todas as chamadas à API. O backend define
`creator_access` e `creator_refresh` como `HttpOnly`; JavaScript não deve tentar
ler esses cookies nem usar `localStorage` para guardar tokens.

O cookie `creator_csrf` é legível pelo SPA e usa `Path=/`. Envie seu valor em
`X-CSRF-Token` para toda requisição `POST`, `PUT`, `PATCH` ou `DELETE`. Se o
cookie CSRF não estiver disponível, chame `GET /api/v1/auth/csrf` após
restaurar a sessão. A resposta de CSRF e as respostas de autenticação usam
`Cache-Control: no-store`.

O access usa `HttpOnly`, `Secure` em produção, `SameSite=Lax` e
`Path=/api/v1`; o refresh usa `HttpOnly`, `Secure` em produção,
`SameSite=Strict` em same-site e `Path=/api/v1/auth`. Nenhum cookie define
`Domain`. Os `Max-Age` acompanham os TTLs configurados e nunca ultrapassam
`AUTH_SESSION_ABSOLUTE_TTL_DAYS`.

Implemente refresh single-flight: a primeira requisição que receber `401`
inicia `POST /api/v1/auth/refresh`; requisições concorrentes aguardam a mesma
Promise e não iniciam outra rotação. O refresh não recebe corpo no contrato
final. `409 REFRESH_IN_PROGRESS` significa que outra aba já venceu a rotação;
aguarde e tente novamente. Depois de um `401` de refresh, descarte o estado da
aplicação e encaminhe o Principal para login.

Para SPA e API em origens diferentes, use `credentials: "include"`, uma origem
explicitamente permitida e o perfil SameSite compatível. `SameSite=None`
cross-site exige HTTPS, `Secure` e allowlist explícita; wildcard não é aceito.

O contrato após o cutover usa apenas cookies de sessão. Login, signup e refresh
não retornam access ou refresh no JSON, e `Authorization: Bearer` não autentica
nem dispensa CSRF. As flags de transição não existem na nova imagem.

## Liberação e rollback

Antes de liberar o cutover, obtenha sign-off explícito do frontend e comunique
o prazo de depreciação aos clientes afetados. Registre links para ambas as
evidências na [issue #128](https://github.com/labLima/creator-backend/issues/128);
ambos os requisitos permanecem pendentes até essa confirmação.

Mantenha a imagem imediatamente anterior disponível durante uma release. Se
for necessário reverter nesse período, implante essa imagem e configure nela:

```text
AUTH_COOKIE_SESSIONS_ENABLED=false
AUTH_LEGACY_BEARER_ENABLED=true
AUTH_TOKEN_BODY_ENABLED=true
```

Antes de encaminhar requisições para a imagem anterior, configure o proxy para
remover o header `Cookie` de todas as requisições à API. Isso é obrigatório: as
rotas de refresh, CSRF e logout ainda podem ler o cookie de refresh mesmo com
a flag de cookies desabilitada. Valide o bloqueio no proxy antes do tráfego;
assim, cookies antigos são ignorados. Clientes devem usar Bearer e os tokens do
login; a imagem anterior não aceita refresh por JSON, portanto precisam fazer
novo login quando o access expirar. As flags são exclusivas da imagem anterior
e não revertem a nova imagem. Não há migration de banco para trocar o transporte.
Após uma release, retire a imagem anterior do plano de rollback.

## Teste de navegador

O fluxo de autenticação por cookies também é exercitado em Chromium real pelo
teste `tests/e2e/test_browser_cookie_auth.py`. Execute localmente com
`python -m playwright install chromium` e `pytest -q --no-cov
tests/e2e/test_browser_cookie_auth.py`. O job `e2e` do GitHub Actions instala
Chromium e executa esse teste junto aos demais fluxos E2E.

O teste sobe a API em HTTPS com certificado temporário para validar cookies
`Secure`, `HttpOnly`, `SameSite` e `Path` usando o cookie jar do navegador. No
ambiente Windows local, o servidor Uvicorn em thread é ignorado devido à
limitação do loop asyncio; o job Linux no CI executa o teste.
