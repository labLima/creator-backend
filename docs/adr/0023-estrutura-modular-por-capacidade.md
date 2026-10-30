# ADR-023: Estrutura modular por capacidade

- Status: accepted
- Data: 2026-10-30
- Owner da decisão: arquitetura
- Owner de manutenção: backend/platform
- Issues de implementação: [0045](../issues/0045-modular-structure-tracker.md)

## Contexto

O backend cresceu por camada técnica: `api/`, `application/`, `domain/`,
`services/`, `repositories/`, `infrastructure/`. Qualquer mudança em uma
entidade atravessava seis diretórios, e a camada HTTP concentrou-se em um único
`main.py` com **5.722 linhas, 222 decorators de rota, 52 serializers e 307
chamadas diretas a repositório**. O `AGENTS.md` já exigia que rotas nascessem em
`APIRouter`, e a regra era violada em 221 de 222 rotas.

O sintoma mensurável: para alterar o contrato de Brand era necessário editar
`models/`, `repositories/`, `infrastructure/persistence/repositories/`,
`api/dtos/`, `main.py` e os testes. Não havia um lugar onde a entidade estivesse
inteira.

## Decisão

Adotar **modular monolith por capacidade** sob `src/creator/modules/<entidade>/`:

```
modules/<entity>/
├── router.py       # APIRouter; só tradução HTTP
├── schemas.py      # DTOs Pydantic da entidade
├── service.py      # casos de uso (quando há regra de negócio)
├── ports.py        # Protocolos + records da entidade
├── policy.py       # autorização específica (quando difere de role check)
├── exceptions.py   # erros próprios (quando existem)
└── adapters/
    ├── tables.py       # ORM SQLAlchemy
    └── repository.py   # implementação do repositório
```

Mantidos como infraestrutura transversal: `core/` (config, paginação, base
Pydantic), `domain/` (shared kernel), `api/` (composição, dependências,
respostas, erros, OpenAPI), `providers/`, `infrastructure/`, `workers/` e
`prompts/`.

### Regra de direção de import

| Origem | Pode importar |
|---|---|
| `domain/` | nada do projeto |
| `core/` | nada do projeto |
| `modules/*/schemas.py`, `ports.py` | `core`, `domain` e `schemas`/`ports` de outro módulo |
| `modules/*/service.py` | próprios `schemas`/`ports`, `uow`, `providers`, `domain` |
| `modules/*/router.py` | próprio `service`/`schemas`, `api.dependencies`, `api.responses`, `api.errors` |
| `modules/*/adapters/**` | próprios `ports`, `infrastructure.db`, SDKs de fornecedor |
| `infrastructure/**` | `core`, `providers`, adapters de módulo |
| `api/**` | routers de módulo |
| `workers/**` | `service` de módulo, `uow`, `infrastructure` |

**Proibido, e verificado por `tests/test_module_boundaries.py`:**

- `service.py`, `schemas.py`, `ports.py` importarem `sqlalchemy`, `fastapi` ou `creator.infrastructure`;
- um módulo importar `service.py`, `router.py` ou `adapters/` de outro;
- qualquer módulo importar `creator.main`;
- ciclos no grafo de import entre módulos.

O `UnitOfWork` (`src/creator/uow.py`) é a única costura de integração entre
capacidades em tempo de execução: um módulo lê dados de outro via
`uow.<repositório>`, nunca importando o serviço alheio.

### Consequências

**Positivas**

- `main.py` passou de 5.722 para 174 linhas; `create_app()` só compõe.
- 27 capacidades autocontidas; adicionar uma rota é criar `router.py` no módulo e
  registrá-lo em `api/router.py`.
- A regra "SQLAlchemy fica na infraestrutura" passou a ser verificada por teste,
  não por convenção.
- Contrato HTTP congelado antes da movimentação (`tests/contracts/`), provando que
  227 operações, 56 tabelas e 48 serializers não mudaram.

**Negativas / custos aceitos**

- Mais arquivos e um nível extra (`adapters/`) em cada módulo.
- Routers ficam fora da meta de cobertura de unidade (medidos por e2e), como já
  acontecia com `creator.api` e `creator.main` antes.
- O `UnitOfWork` continua agregando muitos atributos; a consolidação por
  agregado é trabalho incremental, não um big bang.

### Não-objetivos

- Renomear `src/creator` para `app/`.
- Gerar `docs/openapi.yaml`; o documento continua escrito à mão (ADR-007).
- Alterar `operationId`, paths ou corpos de resposta. Nomes de handler são
  contrato publicado e não podem ser renomeados.
- Renomear caminhos de job do RQ persistidos no Redis.

## Rollback

Mudança puramente de código: reverter por fase (`git revert` de um commit de
fase) não exige migração de dados. A única migração da série,
`0004_drop_dead_tables`, tem `downgrade()` que recria as cinco tabelas com o DDL
original.

## Critérios de aceite

- [x] `grep -c '@application\.' src/creator/main.py` → 0
- [x] `tests/test_route_table_contract.py` verde (227 operações idênticas)
- [x] `tests/test_schema_inventory.py` verde (51 tabelas, DDL byte a byte)
- [x] `tests/test_module_boundaries.py` verde
- [x] `make check`, `make e2e`, `make migrate-check` verdes
- [x] ORM migrado para `modules/*/adapters/tables.py` (51 tabelas, DDL idêntico)
- [x] `SqlAlchemyUnitOfWork` herda `UnitOfWork`; `mypy --strict` verifica paridade
- [ ] Consolidação dos repositórios por agregado (47 → ~30)
