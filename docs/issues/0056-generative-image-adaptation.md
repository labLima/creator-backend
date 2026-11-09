# 0056 — Desdobramento generativo de Content IMAGE

- Status: planejado
- ADR primária: [ADR-027](../adr/0027-generative-image-adaptation.md)
- Issue tracker: [#154](https://github.com/labLima/creator-backend/issues/154)
- Implementação de contrato/Job: [#155](https://github.com/labLima/creator-backend/issues/155)
- Implementação Provider: [#156](https://github.com/labLima/creator-backend/issues/156)
- Relacionadas: [#141](https://github.com/labLima/creator-backend/issues/141), [#147](https://github.com/labLima/creator-backend/issues/147), [#152](https://github.com/labLima/creator-backend/issues/152)

## Objetivo

Estender o fluxo existente de Generation Job IMAGE/TRANSFORM para adaptar uma
imagem real a dimensões de destino por edição generativa, preservando escala
percebida, qualidade e coerência visual. A saída é uma Variation persistida como
nova Content Version; a origem permanece intacta. A feature existente no Creator
do Lovable é somente referência funcional; esta issue implementa o suporte na
API deste repositório e não inclui alterações no Lovable ou trabalho de
interface.

## Critérios de aceite

- [x] ADR-027 aprovada com estratégia de edição generativa, Content Version de
      origem, destinos permitidos, limites de preservação e trade-offs.
- [ ] O TRANSFORM existente identifica a Content Version exata e aceita apenas
      1080×1080, 1080×1350, 1080×1920 e 1920×1080 nesta entrega.
- [ ] O adapter Provider-neutral recebe os bytes da versão autorizada e destino;
      saída tem formato, dimensões e proporção validados, sem geração textual ou
      fallback para crop/resize.
- [ ] Texto aprovado e Brand Assets são compostos deterministicamente conforme
      ADR-026 quando disponíveis; toda Variation exige Human Review antes de
      liberação e pode ser rejeitada sem alterar a origem.
- [ ] Saída é nova Content Version do mesmo Content, vinculada à origem. Storage
      privado, retries limitados/idempotentes, falhas sanitizadas e limpeza de
      temporários são cobertos.
- [ ] Fixtures de proporções distintas, verificações determinísticas e
      checklist visual cobrem escala, continuidade, cortes e coerência.
- [ ] Credits e Provider Usage seguem a política existente; a implementação
      documenta a lacuna atual, sem introduzir cobrança nesta entrega.
- [ ] Contrato/OpenAPI e teste de paridade são atualizados antes da mudança da
      API; testes cobrem isolamento, idempotência, falhas e retry.
- [ ] `make check`, `make security` e `make e2e` passam.

## Evidência

Registrar evidência de CI antes do fechamento das issues de implementação.
