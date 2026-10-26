# ADR-020: Autenticação própria do Creator

- Status: accepted
- Fonte: decisão da Fase -1, 2026-10-26
- Tracker: [#92](https://github.com/labLima/creator-backend/issues/92)
- Issues: [#93](https://github.com/labLima/creator-backend/issues/93), [#94](https://github.com/labLima/creator-backend/issues/94), [#95](https://github.com/labLima/creator-backend/issues/95), [#96](https://github.com/labLima/creator-backend/issues/96)

## Contexto

A autenticação dependia do Supabase Auth. O produto precisa de autenticação própria, com controle de sessão, rotação de refresh token e independência de um provedor externo.

## Decisão

O Creator emite e valida seus próprios tokens:

- Senhas usam Argon2id com parâmetros padrão do `argon2-cffi` e política mínima configurável (`AUTH_PASSWORD_MIN_LENGTH`).
- Access tokens são JWTs HS256 de curta duração, com `iss`, `aud`, `sub` (UUID do User), `session_id`, `role`, `type=access`, `iat`, `exp` e `jti`.
- Refresh tokens são valores opacos aleatórios; apenas o hash SHA-256 é persistido em `auth_sessions`.
- Cada login cria uma família de sessão. O refresh rotaciona o token; reuso de um refresh revogado revoga a família inteira.
- Logout revoga a sessão. `get_current_user` verifica se a sessão ainda está ativa antes de autorizar a requisição.
- Erros não revelam existência de conta; senha ausente usa verificação de hash dummy para reduzir enumeração por timing.
- `AUTH_JWT_SECRET` é obrigatório quando `AUTH_REQUIRED=true`; a aplicação falha fechada sem ele.

## Consequências

O Creatorus deixa de depender do Supabase Auth. A migração de usuários existentes exige redefinição de senha, pois hashes do Supabase não são importáveis. Supabase Storage permanece opcional e separado desta decisão.

A sessão é validada no boundary de `get_current_user`, o que adiciona uma leitura de `auth_sessions` por requisição autenticada. O custo é aceitável para o volume atual e pode ser otimizado com cache sem alterar o contrato.

## Fora de escopo

MFA, verificação de email e password reset ficam para issues futuras.
