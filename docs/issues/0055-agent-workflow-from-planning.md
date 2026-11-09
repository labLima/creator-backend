# Issue 0055: iniciar Agent Workflow a partir de Planning

- ADR primária: [ADR-014](../adr/0014-agent-image-generation-workflow.md)
- Issue GitHub: [#153](https://github.com/labLima/creator-backend/issues/153)
- Milestone: `03 · Fase 2 — Produto Core`
- Relacionadas: [#50](https://github.com/labLima/creator-backend/issues/50), [#143](https://github.com/labLima/creator-backend/issues/143)

## Contexto

O Generation Job independente aceita `planning_id` e `post_structure_id` para
criar imagem, conforme #143. O Agent Workflow completo ainda recebe campanha e
persona como texto livre e não preserva vínculo com o calendário editorial.

## Objetivo

Permitir iniciar o Agent Workflow completo a partir de um Planning autorizado e
uma Post Structure, montar o contexto dos especialistas a partir dos dados
persistidos e manter rastreabilidade até o Content gerado.

## Critérios de aceite

- [x] Aceitar `planning_id` e `post_structure_id` opcionais; quando um for
      enviado, ambos são obrigatórios e a Post Structure deve pertencer ao Planning.
- [x] Autorizar o acesso pela Brand do Planning e validar Workspace/Brand da
      Campaign, Persona e Post Structure; derivar Workspace dos dados autorizados.
- [x] Montar contexto de Campaign e Persona (objetivos, público, voz e perfil),
      Planning (período e orientações gerais) e Post Structure (objetivo, ideia,
      mensagem, headline, CTA, orientação de arte, formato, ratio e resolução).
- [x] Cada execução gerar a peça selecionada. Metas de volume do Planning não
      definem implicitamente a quantidade de uma execução.
- [x] Persistir referências de Planning e Post Structure no Agent Workflow e no
      Content produzido.
- [x] Preservar compatibilidade de pedidos standalone existentes.
- [x] Atualizar `docs/openapi.yaml` antes da mudança de comportamento e manter
      paridade com `app.openapi()`.
- [x] Cobrir validação, autorização, isolamento cross-Workspace, montagem de
      contexto, persistência, compatibilidade e retries idempotentes.
- [x] Passar testes focados, `make check`, `make security` e `make e2e`.

## Nota arquitetural

Estender ADR-014 se a implementação for apenas uma extensão do contrato. Criar
nova ADR se surgir uma decisão arquitetural material.
