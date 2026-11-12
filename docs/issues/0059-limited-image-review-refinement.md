# 0059 — ciclo limitado de Automated Review para IMAGE independente

- ADR primária: [ADR-029](../adr/0029-limited-image-review-refinement.md)
- Issue tracker: [#167](https://github.com/labLima/creator-backend/issues/167)
- Implementação: [#168](https://github.com/labLima/creator-backend/issues/168)
- Relacionada: [#78](https://github.com/labLima/creator-backend/issues/78)

## Objetivo

Transformar a revisão opcional de IMAGE em um ciclo limitado de gerar, avaliar e
corrigir, usando Briefing e Brand Context sem substituir Human Review.

## Critérios de aceite

- [x] Reviewer recebe critérios explícitos para proporção, enquadramento,
      objetos cortados, consistência espacial, texto inesperado e aderência.
- [x] `REFINE` exige correção concreta e preserva o Creative Concept.
- [x] Máximo configurável e estados observáveis para aprovação, exaustão e falha.
- [x] Recusa do Provider durante uma correção encerra o Generation Job com
      `failure_code` estruturado.
- [x] Candidato terminal permanece no Generation Job e Workspace originais.
- [x] Telemetria registra latência por avaliação e custo estimado disponível do
      Provider; correlação inclui Generation Job, Workspace e request ID.
- [ ] Evidências de `make check`, `make security`, `make e2e` e CI antes do
      fechamento.
