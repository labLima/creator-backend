# 0058 — Referências visuais autorizadas para o Artist

- ADR primária: [ADR-028](../adr/0028-authorized-artist-reference-images.md)
- Issue tracker: [#148](https://github.com/labLima/creator-backend/issues/148)
- Relacionada: [#78](https://github.com/labLima/creator-backend/issues/78)

## Objetivo

Permitir upload, seleção ordenada e envio seguro de imagens de referência aos
providers de imagem nos Generation Jobs IMAGE e Agent Workflows.

## Critérios de aceite

- [x] Upload privado valida formato, tamanho, dimensões e checksum; rollback limpa storage.
- [x] Só Assets do Workspace e Brand autorizados e de origem segura são aceitos.
- [x] Até quatro IDs ordenados persistem no input e no fingerprint de idempotência.
- [x] Workers revalidam lifecycle e bytes antes de chamar providers.
- [x] TRANSFORM mantém a fonte antes das referências; falhas não ignoram referências.
- [x] OpenAPI, testes de paridade, isolamento, formatos, limites e indisponibilidade cobertos.
- [x] `make check`, `make security` e `make e2e` passam localmente.

## Evidência local

- `make check`: 653 testes passaram; lint, formatação, mypy e migrações passaram.
- `make security`: pip-audit sem vulnerabilidades conhecidas (4 ignoradas pela configuração) e Gitleaks sem achados.
- `make e2e`: 28 passaram e 1 foi ignorado, incluindo formato inválido, limite e rollback do upload.
