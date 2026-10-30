# 0046 — Backlog de segurança exposto pela refatoração modular

- ADR: [ADR-023](../adr/0023-estrutura-modular-por-capacidade.md)
- Status: aberto
- Origem: auditoria de segurança da branch `refactor/modular-structure`
- Owner: backend/platform + segurança

## Natureza

Todos os itens abaixo são **pré-existentes**: a refatoração moveu código sem
alterar comportamento, e o contrato congelado em `tests/contracts/` confirma que
nenhuma rota, schema ou resposta mudou. A movimentação apenas tornou os defeitos
visíveis, porque agora cada um tem um arquivo de módulo próprio.

Nenhum item foi corrigido dentro da refatoração: alterar autorização no mesmo
commit de uma mudança estrutural impede provar qual das duas causou uma quebra.

## Itens

### S1 — Brand Settings sem vínculo entre `brand_id` e `workspace_id` (alto)

`modules/brand/router.py` autoriza `payload.workspace_id`, mas o `upsert` do
repositório busca a linha apenas por `brand_id`
(`infrastructure/persistence/repositories/core.py`). Um editor de um Workspace
que conheça o UUID de uma Brand de outro Workspace pode ler ou sobrescrever as
Brand Settings da vítima. O UUID da Brand nunca foi tratado como segredo.

Correção: resolver a Brand pelo caminho autorizado (`brands.get_for_user`) e
usar o `workspace_id` resultante; ou filtrar o `upsert` por `brand_id` **e**
`workspace_id`. Teste de regressão com dois Workspaces.

### S2 — Convites permitem escalada de papel (médio)

`modules/workspace/router.py` aceita `role` como `str` livre e exige apenas
`editor` para criar/editar convites; o `update` é não escopado. Um `viewer`
pode elevar um convite existente para `owner`. Sem endpoint de aceite hoje, o
primitivo é latente.

Correção: validar `role` contra `{owner, admin, editor, viewer}`, exigir
`minimum_role="admin"` e escopar `update`/`soft_delete` por Workspace.

### S3 — Mass assignment via `payload: dict[str, Any]` (médio)

Treze handlers repassam o corpo cru para `repository.add(fields=...)` /
`update(fields=...)`, que faz `setattr` em qualquer coluna. `extra="forbid"` do
`CreatorDTO` é contornado. Permite reparentar registros e forjar linhas de
auditoria entre Workspaces.

Correção: substituir por DTOs explícitos ou filtrar `fields` contra o conjunto
de colunas mutáveis no repositório.

### S4 — Viewer consome orçamento de LLM (médio)

`/content/generate` e `/content/improve` verificam apenas pertencimento ao
Workspace; `viewer` é papel de leitura. O caminho de imagem já exige `editor`.

Correção: exigir `minimum_role="editor"`.

### S5 — Valores financeiros vindos do cliente (médio, latente)

`orders`, `refunds`, `coupon_redemptions` e o ledger de crédito aceitam
`amount_cents`, `discount_percent` e `amount` do corpo sem consultar preço no
servidor. Sem consumidor de checkout hoje, o impacto é latente.

Correção: calcular valores no servidor a partir de `credit_packages`/`plans` e
tornar o ledger estritamente append-only (ADR-019).

### S6 — 22 DTOs herdam `BaseModel` em vez de `CreatorDTO` (baixo)

Sem `extra="forbid"` e, em vários casos, sem `max_length`/limites numéricos.
Distribuídos em `credit_package`, `payment_method`, `billing_provider`, `brand`,
`order`, `credit`, `coupon`, `refund`, `billing_account`, `design_structure`.

Correção: um teste que exija `CreatorDTO` e limites em todo `*Request`.

### S7 — `/metrics` sem autenticação e ausência de limite de corpo (baixo)

`api/system.py` expõe métricas sem auth; não há limite de tamanho de corpo para
os `dict[str, Any]`; sem `--proxy-headers` o rate limit por IP atrás de proxy
vira um balde global.

## Fora de escopo

- Dependências (`pip-audit`) e varredura de segredos (`gitleaks`) precisam ser
  executadas no CI: o ambiente local não tinha `gitleaks`.
