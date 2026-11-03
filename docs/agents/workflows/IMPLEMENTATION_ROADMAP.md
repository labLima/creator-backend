# Plano de implementação

## Etapa P0 — infraestrutura de contratos e MVP controlado

1. Cadastrar agentes/subagentes como módulos versionados, não como prompts espalhados pelo backend.
2. Criar validação por JSON Schema, `CreationRun` persistido, inventário de assets e provenance.
3. Implementar AGT-01 completo com 4 perfis de subagentes (podem compor uma chamada).
4. Implementar AGT-02 com `CreativeBlueprint` fiel ao documento original; explorar três territórios antes da escolha.
5. Implementar AGT-03 com SUB-08 e adaptador de geração, sem reinterpretar conceito.
6. Implementar AGT-04 com pontuação server-side, bloqueios e encaminhamento.
7. Aplicar texto/logo como overlay quando exatidão for requisito.
8. Testar ponta a ponta com ao menos 10 briefings de marcas e estilos distintos, anotados por avaliadores humanos.

**Aceite do P0:** pedido completo → contexto rastreável → blueprint válido → primeira imagem → QA → aprovação ou ação justificada, sem loop infinito ou claims inventados.

## Etapa P1 — precisão e eficiência

- Histórico de peças aprovadas como referência de marca com versão, permissão e similaridade controladas.
- QA visual com checagem de zonas seguras e texto esperado.
- Cache de contextos por hash de marca/persona/campanha/referências.
- Reuso de componentes aprovados e edições parciais.
- Painel interno de custo por render, taxa de aprovação na primeira tentativa e motivos de falha.
- Feedback humano categorizado e conectado à causa do pipeline.

## Etapa P2 — evolução

- Experimentos A/B de direção criativa e políticas de prompt.
- Adaptação do blueprint para vídeo e formatos multicanal, sem mudar a lógica de governança.
- Avaliação offline de originalidade, brand fit e persona fit por rubricas calibradas com humanos.
- Recomendações automáticas de melhoria de brand profile/persona quando briefs geram resultados genéricos repetidos.

## Backlog técnico sugerido

### Backend

- `agents.registry.ts`: IDs, versões, permissões e prompts.
- `orchestrator.service.ts`: máquina de estados, limites e handoffs.
- `context.service.ts`, `blueprint.service.ts`, `production.service.ts`, `qa.service.ts`.
- `imageProvider.adapter.ts`, `composition.service.ts`, `scoreCalculator.ts`.
- `creativeSchemas.ts` ou schemas JSON compilados, com validação de saída.

### Persistência

- `creative_runs` — run_id, status, workspace, gastos, limite, timestamps.
- `creative_artifacts` — artifact_type, version, schema, URI/hash, provenance.
- `creative_run_steps` — agente, versão, input/output IDs, duração e resultados.
- `creative_feedback` — nota humana, falhas e categoria de correção.
- `creative_reference_roles` — assetId, função, regras de uso/não copiar.

### Telemetria

- `first_render_approval_rate`
- `average_renders_per_approved_asset`
- `cost_per_approved_asset`
- `blueprint_revisit_rate`
- `brand_violation_rate`
- `human_override_rate`
- `time_to_first_approved_asset`

Estabelecer metas de KPI somente após baseline real; evitar metas arbitrárias que mascaram falhas de qualidade.


---

