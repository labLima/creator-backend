# Issue 0026: brand knowledge entities

- ADR primária: [`0012-langchain-rag-tool-calling`](../adr/0012-langchain-rag-tool-calling.md)
- ADR tracker: [`docs/issues/0021`](0021-langchain-rag-tool-calling.md)
- GitHub: [#49](https://github.com/labLima/creator-backend/issues/49)
- Labels: `backend`, `database`, `architecture`, `priority-high`, `adr-012`
- Status: **aberta em 2026-11-04; schema anterior removido, reintrodução pendente**

## Contexto

Creator possui `brands`, `brand_settings` e o boundary de RAG/embeddings, mas não
possui persistência ativa para fontes e fragmentos indexáveis. O legado Create
Bloom não deve ser replicado.

O schema `brand_knowledge_documents`/`brand_knowledge_chunks` existiu em uma
entrega anterior, mas foi removido pela migration `0004_drop_dead_tables` porque
não tinha repositório, rota ou caso de uso alcançável. A reintrodução deve vir
junto com o lifecycle de ingestão/recuperação, não como tabela órfã.

## Objetivo

Criar Brand Knowledge por Brand e Workspace para ingestão, chunking, embeddings
e recuperação semântica futura, integrado ao fluxo de Brand Context.

## Modelo esperado

- `brand_knowledge_documents`: `id`, `workspace_id`, `brand_id`, `title`,
  `source`, `metadata`, `created_at`, `updated_at`; avaliar `deleted_at`.
- `brand_knowledge_chunks`: `id`, `workspace_id`, `brand_id`, `document_id`,
  `content`, `embedding`, `chunk_index`, `metadata`, `created_at`.
- Usar UUID, timestamps UTC e FK composta ou restrição equivalente para impedir
  mistura de tenants.
- Manter o modelo independente de SDK de Provider e definir índices para
  `(document_id, chunk_index)` e filtros por `(workspace_id, brand_id)`.
- Definir lifecycle: upload/ingestão, normalização, chunking, indexação,
  atualização, remoção e reindexação.

## Critérios de aceite

- [ ] Migration Alembic reversível e modelos SQLAlchemy implementados.
- [ ] Ownership de Workspace/Brand, tipo de embedding e metadata documentados.
- [ ] Unicidade e índices cobrem ingestão, reprocessamento e recuperação.
- [ ] Repositório/casos de uso impedem acesso cross-Workspace.
- [ ] Lifecycle de criação, atualização, remoção e reindexação é testado.
- [ ] Ingestão e recuperação (#74–#77) usam o mesmo contrato de evidência.
- [ ] Se houver API, `docs/openapi.yaml` é atualizado antes da implementação.

## Dependências

- Depends on: `workspaces`, `workspace_memberships`, `brands`.
- Related: ADR-005, ADR-007, ADR-008, ADR-012; issues #20, #21, #22, #74–#77.
