# 0053 — OpenAI como provider ativo de geração

- Status: implementação concluída na branch `fix/openai-provider-ci-recovery`; aguardando merge e CI remoto
- ADR primária: [ADR-001](../adr/0001-llm-provider.md)
- Issue tracker: [#34](https://github.com/labLima/creator-backend/issues/34)
- Issue de implementação GitHub: [#143](https://github.com/labLima/creator-backend/issues/143) (permanece aberta até o merge)

## Objetivo

Usar OpenAI para geração de texto, imagem e revisão multimodal atrás das
interfaces de provider já existentes, incluindo geração de imagem a partir de
um Post Structure pertencente a um Planning.

## Critérios de aceite

- [x] `OPENAI_API_KEY` configura o `LLMProvider`, o `ImageGenerator` e o reviewer.
- [x] OpenAI Images API devolve bytes e metadados normalizados para persistência.
- [x] Generation Job pode receber Planning e Post Structure, validar acesso e
  montar briefing/direção com os dados da peça.
- [x] Content e resposta do Generation Job preservam os IDs de Planning e Post Structure.
- [x] Erros de autenticação, quota, timeout, bloqueio e resposta inválida são
  classificados sem expor a chave nem o corpo sensível do provider.
- [x] Gemini deixa de ser selecionado como provider padrão de geração de texto e
  imagem (permanece apenas como reviewer opcional de compatibilidade, conforme ADR-001).
- [x] Configuração, documentação e evidência de qualidade são atualizadas.

## Evidência local

Branch `fix/openai-provider-ci-recovery`, a partir da `dev` em `c7a7839`:

- `make check` — Ruff, format, mypy strict, pytest (603 testes) e migrate-check verdes;
  cobertura total **75,00%** (gate 73%).
- `make security` — `pip-audit` sem vulnerabilidades conhecidas e Gitleaks sem vazamentos.
- `make e2e` — 18 testes e2e verdes.

## Modelo de imagem

O padrão de `OPENAI_IMAGE_MODEL` é `gpt-image-2.5-sunburst`, com o snapshot
`gpt-image-2.5-sunburst-2026-09-08` disponível para fixação. O valor legado
`gpt-image-2.6-flare` e nomes `gemini-*`/`imagen-*` são normalizados no
carregamento da configuração e no uso (worker e regeneração), sem reescrever o
modelo histórico das gerações já persistidas.

## Nota operacional (RQ)

O formato antigo de job ID (`creator:rq:*`) é inválido no RQ 2.12, que aceita
apenas letras, números, `_` e `-`. Antes do deploy desta branch, drene a fila de
jobs antigos com esse formato; o novo formato é `creator-rq-*` e não renomeia
entrypoints `creator.workers.*`.

Jobs de Planning enfileirados antes desta correção não têm `resolved_input` e
devem ser reenfileirados após o deploy. O fallback do worker cobre apenas jobs
standalone legados que ainda carregam `briefing`/`direction` no `request_input`.
