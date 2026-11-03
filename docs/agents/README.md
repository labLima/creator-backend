# Creator — especificação de agentes

**Estado:** material misto; consulte o status de cada documento antes de tratá-lo como contrato. A proposta criativa original não foi adotada como comportamento do produto.

## Índice

- [Arquitetura proposta e decisões vigentes](ARCHITECTURE.md)
- [Inventário e mapeamento normativo](AGENTS_AND_SUBAGENTS.md)
- [Mapa de domínio: proposta × runtime atual](DOMAIN-MAPPING.md)
- [Agentes principais](agents/)
- [Subagentes como responsabilidades lógicas](subagents/)
- [Contratos implementados e ausentes](schemas/README.md)
- [Workflows e rubrica em proposta](workflows/)
- [Exemplos](examples/README.md)

## Fonte normativa

O fluxo implementado é Business → Planner → Writer → Artist → Reviewer, seguido das decisões de entrega do Agent Workflow, conforme [ADR-014](../adr/0014-agent-image-generation-workflow.md), [ADR-017](../adr/0017-versioned-agent-pipeline-contracts.md) e [ADR-018](../adr/0018-event-driven-agent-pipeline.md). O Creator controla estados, autorização, persistência, retries e outbox; CrewAI é um adapter.

O desenho AGT-01..04/SUB-01..11 abaixo é uma proposta conceitual. Não declara que os schemas, os agentes separados, o Creative Blueprint ou a rubrica ponderada já existam no runtime.

## Stack

As recomendações são independentes de linguagem e fornecedor. A implementação existente usa Python, FastAPI, SQLAlchemy e SQLite; consulte ADR-021/024. Esta proposta não autoriza uma migração de stack.

