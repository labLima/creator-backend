# ADR-019: Ledger de créditos por Workspace

- Status: accepted (amended 2026-11-13)
- Tracker: [#38](https://github.com/labLima/creator-backend/issues/38)
- Issue: [0031-credits](../issues/0031-credits.md)
- Relacionadas: [ADR-029](0029-sqlite-final-schema-alignment.md) (paridade com o modelo final), [ADR-020](0020-self-hosted-authentication.md) (autenticação própria), [ADR-021](0021-sqlite-default-database.md) (SQLite como banco padrão)
- Implementação: [#162](https://github.com/labLima/creator-backend/issues/162), revisão `0035_credit_ledger_alignment`

## Histórico

> **Estado em 2026-11-04:** as tabelas `credit_wallets`, `credit_transactions` e
> `credit_prices` foram removidas pela migration `0004_drop_dead_tables` por não
> terem repositório/caso de uso. O código atual só possui
> `workspace_credit_transactions` genérico. Esta ADR permanece como alvo de
> implementação; a #54 foi corrigida para refletir a lacuna.
>
> **Emenda de 2026-11-13:** a modelagem final foi implementada pela T15 (#162).
> O alvo descrito originalmente — uma linha `credit_wallets` por Workspace,
> `credit_transactions`, `credit_prices` globais e uma coluna `idempotency_key`
> — não é o modelo persistido. `credit_wallets`, `credit_transactions` e
> `credit_prices` não voltam: o saldo é derivado do ledger e dos lotes, e a
> tabela viva é `workspace_credit_transactions`. A decisão abaixo substitui a
> de 2026-11-04; o restante do histórico é preservado.

## Decisão

Créditos são unidades inteiras e não monetárias, consumidas por uma Generation
ou Agent Workflow e registradas por Workspace. O modelo final é composto por
**três tabelas**:

| Tabela | Papel |
| --- | --- |
| `workspace_credit_transactions` | Ledger append-only; uma linha por movimento de crédito, com `type`, `amount` e `balance_after`. |
| `workspace_credit_lots` | Lotes de concessão: `original_amount`, `remaining_amount` e `expires_at`; um lote nasce de uma transação de concessão positiva. |
| `workspace_credit_lot_consumptions` | Alocação de um débito a um lote (`lot_id`, `transaction_id`, `amount > 0`), imutável. |

Não existem `credit_wallets` nem `credit_prices`. O saldo não é uma linha
persistida que precisa ser atualizada em paralelo ao histórico; ele é derivado.

### 1. Duas medidas de saldo, nunca sinônimos

- **Saldo do ledger — `balance_after`.** É o `SUM(amount)` acumulado por
  Workspace, na ordem `(created_at, id)`, congelado no momento da inserção.
  Representa a história de movimentos e **não expira**: um crédito concedido em
  janeiro continua no ledger depois de expirar como disponibilidade. O CHECK
  `chk_credit_tx_balance_nonnegative` impede que o acumulado fique negativo.
- **Créditos disponíveis.** É o `SUM(remaining_amount)` dos lotes com
  `expires_at IS NULL OR expires_at > now()`, conforme a função
  `workspace_credit_balance` do modelo final. É o número que uma Generation pode
  gastar; lotes expirados valem zero mesmo que o ledger ainda os registre.

Os dois números são distintos e não podem ser publicados com o mesmo nome. O
único agregado persistido é o snapshot `balance_after` por transação, para
auditoria e recálculo; o "Credit Wallet" é a leitura derivada, não uma tabela.

**Expiração é eager.** Um lote vencido deve gerar uma transação `EXPIRATION`
com `amount < 0`, escrita atomicamente com a redução do `remaining_amount` do
lote, em vez de o sistema apenas filtrar lotes vencidos na leitura. Sem isso, o
ledger e os créditos disponíveis divergem sem rastro auditável. O caso de uso de
expiração (agendador/worker) é implementação futura; o schema já aceita o
movimento.

### 2. `type`, sinal e colunas de referência dedicadas

`type` usa o vocabulário `credit_transaction_type`:

| `type` | Sinal de `amount` | Uso |
| --- | --- | --- |
| `SUBSCRIPTION_CREDIT` | `> 0` | Concessão do ciclo/assinatura; materializa um lote. |
| `TOP_UP` | `> 0` | Compra avulsa de créditos; materializa um lote. |
| `COUPON_CREDIT` | `> 0` | Crédito concedido por cupom; materializa um lote. |
| `REFUND` | `> 0` | Estorno de um consumo anterior. |
| `GENERATION` | `< 0` | Consumo de uma Generation ou Agent Workflow. |
| `EXPIRATION` | `< 0` | Expiração de um lote. |
| `ADJUSTMENT` | `≠ 0` | Correção administrativa, aceita qualquer sinal. |

O CHECK `chk_credit_tx_amount_by_type` materializa a regra de sinal;
`chk_credit_tx_amount_nonzero` rejeita `amount = 0`, de modo que nenhum
movimento nulo torne `balance_after` ambíguo.

A correlação é feita por **quatro colunas dedicadas** — `order_id`,
`invoice_id`, `generated_image_id` e `image_resize_id` —, no lugar do trio
genérico `reference_type`/`reference_id`. No máximo uma delas é preenchida
(`chk_credit_tx_single_reference`). `order_id` tem FK composta
`(order_id, workspace_id) -> orders(id, workspace_id)`; os demais alvos usam FK
`RESTRICT`, `workspace_id` usa `RESTRICT` e `created_by` usa `SET NULL`. A
correlação técnica com Provider Usage (#23) continua em telemetria separada; o
ledger aponta para a imagem/resize gerada, não duplica o evento do provider.

### 3. Append-only e correções

`workspace_credit_transactions` não tem `updated_at` nem `deleted_at`: é
append-only. Correções são novos movimentos (`REFUND`, `ADJUSTMENT`,
`EXPIRATION`), nunca `UPDATE` ou delete lógico. Os lotes são mutáveis apenas em
`remaining_amount`/`updated_at`, e as linhas de consumo são imutáveis.

O enforcement no banco (triggers/guards de imutabilidade, recálculo de
`balance_after` e validação de procedência da imagem) pertence à **T20** e
**não está implementado**. Até lá, a garantia é a API somente leitura mais os
casos de uso internos, e o CHECK de não negatividade.

### 4. Idempotência natural, sem `idempotency_key`

Não existe coluna de chave de idempotência. A idempotência vem dos UNIQUEs por
alvo e tipo:

- `(order_id, type)`
- `(invoice_id, type)`
- `(generated_image_id, type)`
- `(image_resize_id, type)`

Uma repetição do mesmo grant/spend para o mesmo alvo e tipo viola o UNIQUE em
vez de duplicar o movimento; o caso de uso traduz a violação em "já aplicado".
Como NULLs não colidem em índice UNIQUE do SQLite, uma transação sem referência
não é protegida por essa regra: o caso de uso que escreve deve preencher a
coluna dedicada correspondente. `ADJUSTMENT` e `EXPIRATION` sem alvo continuam
válidos, mas não são idempotentes por esse mecanismo.

### 5. A superfície HTTP é somente leitura

Um Credit Transaction é append-only, então a API publica apenas:

- `GET /api/v1/workspace-credit-transactions` (lista, com filtro opcional por
  `workspace_id`);
- `GET /api/v1/workspace-credit-transactions/{id}`.

`POST` e `DELETE` foram removidos do contrato: nenhum cliente escreve ou apaga
ledger. Concessões e consumos pertencem a casos de uso de aplicação —
billing/assinatura para grants, generation para spends —, que escrevem pelo
`UnitOfWork` e pelos ports da capability, no mesmo commit do efeito de negócio.
Preços por ação não são persistidos no modelo final; se o produto os adotar,
será uma decisão nova, não o retorno de `credit_prices`.

### 6. Isolamento de Workspace e autenticação

Toda linha carrega `workspace_id` e o acesso é sempre por Workspace. A leitura
HTTP passa pelo Principal autenticado da ADR-020 e por uma Membership `ACTIVE`;
o `workspace_id` enviado pelo cliente é apenas filtro, nunca autorização. A
escrita interna deve derivar o Workspace do recurso que a origina e validar que
as referências pertencem a ele (a FK composta cobre `order_id`; a procedência de
imagem/resize é validação de aplicação até a T20).

A emenda da ADR-029 que preserva `users.password_hash`/`users.global_role` não
altera o ledger: `created_by` referencia `users(id)` com `SET NULL`, então a
remoção de um usuário não apaga nem reescreve o histórico.

## Consequências

- O saldo é auditável e reproduzível a partir do ledger e dos lotes; não há
  linha de wallet para dessincronizar.
- Publicar apenas um dos dois saldos induz decisão de consumo errada; o contrato
  e a documentação precisam nomeá-los de forma distinta.
- O ledger cresce indefinidamente e correções adicionam linhas; retenção e
  agregação são preocupações operacionais futuras.
- Escritas concorrentes no mesmo Workspace precisam de serialização no caso de
  uso; o SQLite não oferece `SELECT ... FOR UPDATE`, então o lock é o do
  transaction/`UnitOfWork`.
- Enquanto a T20 não trouxer os triggers, `balance_after` e a procedência de
  imagem/resize dependem dos casos de uso e dos CHECKs/FKs existentes.
- Concessão, consumo e expiração ainda não têm caso de uso implementado; a API
  atual é somente leitura.

## Fora de escopo

- Preço por ação e catálogo de preços (`credit_prices`).
- Reset de allowance mensal, agendador de expiração e job de conciliação.
- Triggers, funções e view do dump (T20).
- Migrar Provider Usage (#23) para dentro do ledger.
