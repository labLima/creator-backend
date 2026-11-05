# 0052 — Generation Jobs independentes com especialistas

- Status: implementação em revisão
- ADR primária: [ADR-025](../adr/0025-generation-independente-com-especialistas.md)
- Issue tracker: [#140](https://github.com/labLima/creator-backend/issues/140)
- Implementação: [#141](https://github.com/labLima/creator-backend/issues/141)

## Objetivo

Permitir a criação, regeneração e transformação assíncrona de COPY, CAPTION e
IMAGE associados a uma Brand autorizada, reutilizando WRITER, ARTIST e a revisão
opcional do REVIEWER sem executar o Agent Workflow completo.

## Critérios de aceite

- [x] Publicar POST e GET de Generation Jobs com autorização e chave de idempotência.
- [x] Usar contratos de saída específicos de COPY e CAPTION no WRITER.
- [x] Gerar IMAGE pelo ARTIST e permitir revisão opcional com decisão e feedback registrados.
- [x] Persistir versões imutáveis de texto, imagens e metadados de prompt/provider.
- [x] Preservar contratos diretos existentes e manter melhoria de texto síncrona, preview-only e alinhada às regras do WRITER.
- [x] Atualizar ADR, OpenAPI, paridade de rotas e inventário de schema.
- [x] Validar `make check`, `make security` e `make e2e`.

## Evidência

- `make check`: Ruff, mypy, 460 testes aprovados, 1 skip, cobertura de 74,18% e migração sem diferenças.
- `make security`: pip-audit sem vulnerabilidades conhecidas além das quatro exceções existentes; Gitleaks sem achados.
- `make e2e`: 17 testes aprovados, 1 skip.
- `git diff --check`: sem erros de whitespace.

## Limite de compatibilidade

Os endpoints diretos de imagem continuam no prompt/worker legado: seus contratos
aceitam Content ou imagem existente e estilo, mas não fornecem direção visual
aprovada para o ARTIST. A troca também não pode afetar jobs legados já
enfileirados. Geração com ARTIST está disponível em `POST /api/v1/generation-jobs`,
que exige Brand e direção; a migração dos consumidores dos endpoints diretos
fica condicionada a poderem fornecer essa direção sem alterar seus contratos.
