# Issue 0037 - Alinhar models e DTOs ao Creator DB

- ADR primária: [ADR-015](../adr/0015-database-diagram-alignment.md)
- Tracker: [ADR-015](../adr/0015-database-diagram-alignment.md)

## Escopo

- [x] Separar DTOs HTTP por contexto sem quebrar imports dos endpoints atuais.
- [x] Inventariar as tabelas do diagrama e seus enums principais.
- [x] Implementar a primeira fatia de models e migration para billing, assinaturas e providers.
- [x] Implementar a primeira fatia de models para campanhas, planejamento e notificações.
- [ ] Validar constraints/índices contra o banco SQLite real (ADR-021).
- [ ] Decidir o destino dos models legados; a migração de comportamento do Create Bloom foi encerrada em 2026-11-04, então remoção exige issue própria com consumidores migrados.
- [x] Atualizar OpenAPI e adicionar testes por fatia.
- [x] Migrar os endpoints de Campaign e Post Structure para os schemas do diagrama, mantendo o conteúdo legado em compatibilidade durante a transição.
- [x] Adicionar endpoints schema-native para Persona, Planning, BrandAsset e leitura de GeneratedImage.

Veja a matriz detalhada em [docs/SCHEMA-MIGRATION-MATRIX.md](../SCHEMA-MIGRATION-MATRIX.md).
