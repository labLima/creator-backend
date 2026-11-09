# 0056 — Desdobramento generativo de Content IMAGE

- Status: planejado
- ADR primária: [ADR-027](../adr/0027-generative-image-adaptation.md)
- Issue tracker: [#154](https://github.com/labLima/creator-backend/issues/154)
- Implementação de contrato/Job: [#155](https://github.com/labLima/creator-backend/issues/155)
- Implementação Provider: [#156](https://github.com/labLima/creator-backend/issues/156)
- Relacionadas: [#141](https://github.com/labLima/creator-backend/issues/141), [#147](https://github.com/labLima/creator-backend/issues/147), [#152](https://github.com/labLima/creator-backend/issues/152)

## Objetivo

Permitir que uma imagem existente seja adaptada a formatos de publicação por
edição generativa, preservando escala percebida, qualidade e coerência visual.
O desdobramento cria uma Variation/Content Version nova e não modifica a origem.

## Critérios de aceite

- [ ] ADR-027 aprovada com estratégia de adaptação, dimensões/origens permitidas,
      limites de preservação e trade-offs.
- [ ] Generation TRANSFORM IMAGE e Generation Job aceitam a solicitação com
      autorização da origem e do Workspace.
- [ ] Edição generativa atende a proporção/dimensões de destino sem depender de
      crop/resize simples como resultado final.
- [ ] Texto, logos e Brand Assets têm tratamento definido para preservar a
      fidelidade exata ou exigir revisão humana.
- [ ] Fonte permanece imutável; saída é uma nova versão vinculada à origem.
- [ ] Contrato, OpenAPI e testes de paridade são atualizados antes da mudança da
      API.
- [ ] Testes cobrem isolamento, validação de entrada, idempotência, falhas e
      retry do Provider.
- [ ] `make check`, `make security` e `make e2e` passam.

## Evidência

Registrar evidência de CI antes do fechamento das issues de implementação.
