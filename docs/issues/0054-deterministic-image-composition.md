# Issue 0054: Composição determinística de IMAGE

- ADR primária: [ADR-026](../adr/0026-deterministic-image-composition.md)
- Tracker: [#152](https://github.com/labLima/creator-backend/issues/152)
- Implementação: [#147](https://github.com/labLima/creator-backend/issues/147)
- Relacionada: [#78](https://github.com/labLima/creator-backend/issues/78)

## Critérios de aceite

- [x] Contratos opt-in para Generation Job IMAGE e Agent Workflow.
- [x] Cena recebe instrução sem texto e composição usa textos explícitos.
- [x] Fonte e marca são Brand Assets autorizados, lidos por caminhos de storage.
- [x] Detecção inconclusiva ou texto detectado impede entrega automática.
- [x] Agent Workflow guarda a cena como Content Version candidata, aguarda revisão
      humana e retoma ARTIST com os mesmos bytes após aprovação.
- [x] Generation Job IMAGE independente guarda a cena em storage e expõe decisão
      humana autenticada; aprovação retoma a composição sem gerar outra cena.
- [x] Rejeição exclui a cena candidata do storage; falhas transitórias deixam
      limpeza pendente para retry periódico pelo worker.
- [x] Resultado preserva dimensões, aplica margem e registra parâmetros e hashes.
- [x] Validar fonte e marca reais via Brand Settings, Brand Assets e storage local
      em teste integrado, incluindo retomada da composição após aprovação humana.
- [x] Gates locais `make check`, `make security` e `make e2e` passaram em 2026-11-06.
- [ ] Registrar evidência de CI antes do fechamento da issue.
