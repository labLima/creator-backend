# ADR-022: Autenticação em cookies com adapter interno do Creator

- Status: accepted
- Fonte: [issue #116](https://github.com/labLima/creator-backend/issues/116), 2026-10-27
- Tracker: [#116](https://github.com/labLima/creator-backend/issues/116)
- Issue local: [0044-cookie-auth-provider](../issues/0044-cookie-auth-provider.md)
- Issues condicionais: [#118](https://github.com/labLima/creator-backend/issues/118), [#119](https://github.com/labLima/creator-backend/issues/119), [#120](https://github.com/labLima/creator-backend/issues/120), [#121](https://github.com/labLima/creator-backend/issues/121), [#122](https://github.com/labLima/creator-backend/issues/122), [#123](https://github.com/labLima/creator-backend/issues/123), [#124](https://github.com/labLima/creator-backend/issues/124), [#125](https://github.com/labLima/creator-backend/issues/125), [#126](https://github.com/labLima/creator-backend/issues/126), [#127](https://github.com/labLima/creator-backend/issues/127), [#128](https://github.com/labLima/creator-backend/issues/128)
- Owner da decisão: arquitetura + segurança
- Owner de manutenção: backend/platform; revisão de segurança obrigatória

## Contexto

A refatoração pede JWT em cookies com CSRF, mas o pacote upstream
`fastapi-jwt-auth` 0.5.0 não é compatível com o runtime atual do Creator:

- a release foi publicada em 2020 e fixa `PyJWT>=1.7.1,<2.0.0`;
- o import falha com Pydantic 2 por causa de `@validator(..., each_item=True)`;
- o código chama `.decode("utf-8")` no retorno de `jwt.encode`, incompatível com
  PyJWT 2;
- a restrição de PyJWT conflita com `PyJWT[crypto]>=2.15,<3` do projeto e com o
  gate de segurança;
- cookies e CSRF são mecanismos de transporte, não devem redefinir o modelo de
  `Auth Session` decidido na ADR-020.

A documentação upstream apresenta cookies HttpOnly e double-submit CSRF, mas
alerta que o exemplo sem CSRF é vulnerável. [PyPI registra a release 0.5.0,
publicada em 2020, e sua dependência `PyJWT<2`](https://pypi.org/pypi/fastapi-jwt-auth/0.5.0/json).

## Evidência de compatibilidade

### Reprodução Python 3.12 + Pydantic 2

Executado em ambiente descartável, sem alterar as dependências do projeto:

```powershell
uv venv tmp\adr022-repro --python 3.12
uv pip install --python tmp\adr022-repro\Scripts\python.exe `
  'fastapi-jwt-auth==0.5.0' 'pydantic>=2,<3'
tmp\adr022-repro\Scripts\python.exe -c `
  "import sys,pydantic; print(sys.version); print(pydantic.__version__); import fastapi_jwt_auth"
```

Resultado observado:

```text
Python 3.12.14
pydantic 2.14.1
TypeError: `@validator(..., each_item=True)` cannot be applied to fields with a schema of json-or-python
```

O código publicado também contém `jwt.encode(...).decode('utf-8')` em
`fastapi_jwt_auth/auth_jwt.py`. Esse comportamento é incompatível com o PyJWT 2,
cujo `jwt.encode` retorna `str`, conforme documentado no [issue upstream
#89](https://github.com/IndominusByte/fastapi-jwt-auth/issues/89). O erro de
import foi reportado no [issue upstream
#98](https://github.com/IndominusByte/fastapi-jwt-auth/issues/98).

### Conflito de resolução

```powershell
uv pip install --dry-run --python tmp\adr022-repro\Scripts\python.exe `
  'fastapi-jwt-auth==0.5.0' 'PyJWT>=2.15,<3'
```

Resultado observado:

```text
No solution found when resolving dependencies
fastapi-jwt-auth>=0.5.0 depends on pyjwt>=1.7.1,<2.0.0
PyJWT>=2.15,<3 is required
requirements are unsatisfiable
```

### Matriz de alternativas

| Alternativa | Python 3.12 / Pydantic 2 / PyJWT 2 | Cookies e CSRF | Ownership e decisão |
| --- | --- | --- | --- |
| `fastapi-jwt-auth==0.5.0` | Reprovada: falha no import e fixa PyJWT 1.x | Possui suporte conceitual | Rejeitada por incompatibilidade e falta de manutenção |
| `another-fastapi-jwt-auth==0.1.6` | Importou com Pydantic 2.14.1 e PyJWT 2.15.1; `jwt.encode` retornou `str` | Mantém o contrato conceitual | Apenas referência; não é dependência do Creator e não possui ownership do Creator |
| Adapter interno equivalente | Compatível por definição com as dependências atuais | Pode implementar cookies/CSRF diretamente | Escolhida; código e manutenção pertencem ao Creator |
| Fork/vendor Creator-owned | Exigiria manter um fork e seu patch de segurança | Mantém apenas o transporte de cookies/CSRF | Rejeitada por custo e superfície de manutenção |

O fork de referência declara suporte a Pydantic 2 e PyJWT 2 em seu próprio
metadata, mas isso não substitui ownership, revisão de segurança ou CI do
Creator. O Creator implementará somente a superfície necessária em
`src/creator/infrastructure/auth/jwt_adapter.py`, usando a dependência PyJWT
2.x do projeto. [Metadata do fork de referência](https://pypi.org/project/another-fastapi-jwt-auth/).

## Decisão

O Creator não adotará `fastapi-jwt-auth` como dependência nem manterá um
fork/vendor do pacote. O transporte de autenticação usará um adapter interno,
Creator-owned, com o menor contrato necessário para:

1. emitir e validar os claims definidos na ADR-020;
2. usar o contrato de string de `jwt.encode` do PyJWT 2;
3. preservar `PyJWT[crypto]>=2.15,<3`;
4. manter cookies e CSRF sob as interfaces internas do Creator;
5. executar CI em Python 3.12 e 3.13 com `pip-audit`.

O adapter ficará confinado à infraestrutura. `application/` e `domain/` não
importarão PyJWT, FastAPI, `Request` ou `Response`. A interface interna
traduzirá a sessão emitida pelo Creator para o transporte HTTP, sem delegar ao
provider a autoridade sobre identidade, `Auth Session` ou Workspace.

## Contrato de autenticação

- Access tokens continuam JWT HS256 com `iss`, `aud`, `sub`, `session_id`,
  `role`, `type=access`, `iat`, `exp` e `jti`, conforme a ADR-020.
- Refresh tokens continuam opacos; somente o hash SHA-256 é persistido.
- Login e refresh continuam criando/rotacionando uma família de `Auth Session`.
- Reuso de refresh revogado continua revogando a família inteira.
- Logout e `get_current_user` continuam consultando o estado revogável no
  Creator; a biblioteca não será a fonte de revogação.
- Nenhuma decisão desta ADR altera isolamento de Workspace, Membership ou
  autorização de Principal.

### Cookies e CSRF

Os nomes concretos (`creator_access`, `creator_refresh` e `creator_csrf`) ficam
sob o namespace do Creator e serão fixados pela issue de política de cookies.
As invariantes são:

- access e refresh são `HttpOnly`;
- cookies de sessão são `Secure` fora do ambiente local;
- access usa `Path=/api/v1` e não define `Domain`;
- refresh usa caminho restrito ao endpoint de refresh e não define `Domain`;
- o cookie CSRF usa `Path=/`, é legível pelo SPA, não contém o token de sessão
  e acompanha o valor no header `X-CSRF-Token`;
- toda requisição autenticada por cookie com método `POST`, `PUT`, `PATCH` ou
  `DELETE` exige CSRF válido;
- o CSRF usa double-submit assinado e vinculado à `Auth Session`;
- `SameSite` é defesa em profundidade, não substituto da validação CSRF.

A política segue a recomendação do [OWASP CSRF Prevention Cheat
Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
e as restrições de [`HttpOnly`, `Secure` e `SameSite`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie).

### Perfis de topologia

| Topologia | Perfil inicial | Requisitos obrigatórios |
| --- | --- | --- |
| Same-origin | Padrão de produção do Creator; `SameSite=Strict` | Proxy mantém SPA e API sob a mesma origem; sem CORS de credenciais |
| Same-site | Permitida quando SPA e API compartilham o site | `credentials` explícito, `SameSite` compatível e Origin validado |
| Cross-site | Permitida somente por decisão de frontend/produto | `SameSite=None`, `Secure`, CORS com allowlist exata, `allow_credentials=true` e sem wildcard |

A topologia padrão aceita é same-origin. Same-site separado e cross-site são
perfis opt-in por ambiente; a configuração cross-site rejeita wildcard de origem
com credenciais.

## Dependência, CI e manutenção do adapter

- O consumidor usa somente `PyJWT[crypto]>=2.15,<3`; não há dependência de
  `fastapi-jwt-auth` nem `PyJWT<2` transitivo.
- O adapter é código do Creator e suas mudanças seguem revisão de código,
  testes de segurança e esta ADR; não há commit upstream para pinar.
- O CI do consumidor cobre Python 3.12 e 3.13, Pydantic 2, PyJWT 2.15+,
  import do adapter, assinatura/verificação e emissão de cookies.
- `pip-audit` será obrigatório e qualquer exceção deverá ser limitada, justificada
  e aprovada por segurança.
- Backend/platform é responsável por acompanhar PyJWT e vulnerabilidades;
  arquitetura aprova mudanças no contrato; segurança revisa releases e o gate.

## Rollback e consequências

- A migração será protegida por feature flag.
- Em rollback, a API desabilita leitura/escrita de cookies, expira cookies
  emitidos e preserva temporariamente Bearer para os clientes existentes.
- Nenhuma migration de banco é necessária para trocar o transporte.
- O custo é manter um adapter e seus testes. O benefício é compatibilidade com
  o runtime atual, auditabilidade e separação entre transporte e domínio.
- A mudança para cookies exige atualização posterior de OpenAPI, CORS, guia do
  SPA e E2E de navegador; todos permanecem fora desta issue.

## Gate de implementação e aceitação

As issues de implementação #118–#128 já existiam no GitHub antes desta ADR e
foram liberadas pelo aceite formal desta decisão. Nenhuma nova issue foi aberta;
o tracker versionado continua sendo o índice para o trabalho de implementação.

Critérios de decisão:

- [x] Reprodução Python 3.12 + Pydantic 2 registrada.
- [x] Conflito `PyJWT<2` versus `PyJWT>=2.15,<3` registrado.
- [x] Matriz upstream/fork de referência/adapter interno registrada.
- [x] Adapter interno Creator-owned escolhido explicitamente; fork/vendor rejeitado.
- [x] Cookies, CSRF, refresh, rotação, revogação, claims, topologias, flags,
      rollback e owners definidos.
- [x] Dependência PyJWT, CI, `pip-audit` e processo de atualização definidos.
- [x] Owner de arquitetura + segurança atribuído e aprovação registrada.
- [x] Status alterado para `accepted` após a aprovação formal.

## Fora de escopo

- MFA, verificação de email, password reset e service tokens.
