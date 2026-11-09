# 0057 — Importação de Content IMAGE

- ADR: [ADR-027](../adr/0027-generative-image-adaptation.md)
- Tracker: [#154](https://github.com/labLima/creator-backend/issues/154)
- Issue de implementação: [#160](https://github.com/labLima/creator-backend/issues/160).

Importar PNG, JPEG ou WebP para um novo Content e primeira Content Version,
sem criar Generation fictícia, para uso pelo IMAGE/TRANSFORM. Validar autoria,
bytes, dimensões, limite e isolamento; preservar storage imutável e limpeza.

Não encerrar sem testes, evidência de CI e issue GitHub vinculada ao tracker.
