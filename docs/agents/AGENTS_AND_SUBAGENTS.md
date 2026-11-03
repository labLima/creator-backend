# Inventário de responsabilidade e handoffs

> **Status:** proposta conceitual. O runtime vigente é Business → Planner → Writer → Artist → Reviewer → DELIVERY. AGT/SUB IDs são mapeamentos de responsabilidade, não agentes executados separadamente. Contratos ativos: [schemas/README.md](schemas/README.md).
>
> **Mapa de artefatos propostos:** [DOMAIN-MAPPING.md](DOMAIN-MAPPING.md) relaciona cada artefato da proposta ao equivalente atual (ou à ausência dele).

| Proposta | Papel atual | Contrato atual | Status |
|---|---|---|---|
| AGT-01 / SUB-01–04 | Business | `BusinessOutput` | Implementado como uma etapa; SUBs são instruções lógicas, não chamadas independentes. |
| AGT-02 / SUB-05–07 | Planner e Writer | `PlannerOutput`, `WriterOutput` | Implementados como duas etapas; o escopo proposto de blueprint único não está adotado. |
| SUB-08 | Writer e Artist | `WriterOutput.direction.visual_prompt`; boundary de imagem | Prompt visual vem de Writer; Artist executa o Provider. Não há pacote SUB-08 tipado. |
| AGT-03 / ADP-01–02 | Artist | `ImageGenerationProvider` e artefatos do workflow | Geração implementada; compositor determinístico e CreativeBlueprint não. |
| AGT-04 / SUB-09–11 | Reviewer | `ReviewOutput` / `ImageReviewResult` | Revisão implementada; subresponsabilidades não são chamadas independentes e a rubrica ponderada não está implementada. |
| ORC-00 | Creator Agent Workflow + Outbox | estados, steps e eventos persistidos | Implementado pelo Creator, conforme ADR-014/017/018. |
| DELIVERY | Worker e persistência do Creator | transições e artefatos finais | Parte do workflow atual; não é um agente. |

## Inventário proposto de componentes

> **Proposta conceitual.** A tabela abaixo descreve o desenho alvo; não é o contrato ativo nem implica agentes/subagentes independentes no runtime.

| ID | Componente | Tipo | Recebe | Entrega |
|---|---|---|---|---|
| ORC-00 | Orquestrador Central | código | CreationRequest | CreationRun e decisões de fluxo |
| AGT-01 | Inteligência Estratégica | agente | fontes de marca/campanha/persona | StrategicContext |
| SUB-01 | Inteligência de Marca | subagente AGT-01 | marca e manual | BrandContext |
| SUB-02 | Inteligência Criativa de Persona | subagente AGT-01 | persona | PersonaCreativeProfile |
| SUB-03 | Estratégia de Campanha | subagente AGT-01 | briefing | CampaignStrategy |
| SUB-04 | Classificador de Referências | subagente AGT-01 | assets | ClassifiedReferences |
| AGT-02 | Diretor Criativo | agente | StrategicContext | CreativeBlueprint |
| SUB-05 | Explorador de Territórios | subagente AGT-02 | problema | 3 conceitos resumidos |
| SUB-06 | Copywriter | subagente AGT-02 | conceito | CopyConcept |
| SUB-07 | Diretor de Arte | subagente AGT-02 | conceito + copy | ArtDirectionConcept |
| AGT-03 | Produção Visual | agente | CreativeBlueprint | VisualPromptPackage + ImageAsset |
| SUB-08 | Visual Prompt Builder | subagente AGT-03 | blueprint | VisualPromptPackage |
| ADP-01 | Gerador de imagem | ferramenta | prompt + refs | ImageAsset base |
| ADP-02 | Compositor de copy/logotipo | ferramenta | imagem base + overlays | ImageAsset final |
| AGT-04 | Crítico Criativo | agente | imagem + blueprint | CreativeQAReport |
| SUB-09 | Guardião de Marca e Produto | subagente AGT-04 | arte + fatos | ComplianceFindings |
| SUB-10 | Inspetor Visual e Técnico | subagente AGT-04 | arte + layout | VisualFindings |
| SUB-11 | Planejador de Correções | subagente AGT-04 | achados | CorrectionPlan |

## O que precisa persistir

- Prompt e versão dos agentes: `agent_id`, `design_version`, `spec_version`, `prompt_template_version`, `model_policy`.
- Cada execução: `run_id`, workspace, request, etapas, state, tentativas, consumo, erros.
- Artefatos: context, blueprint, prompt package, assets, QA e relação entre versões.
- Referências com `referenceRole`, origem/permissões de uso e regra de não copiar.
- Decisões de aprovação (sistema e/ou humano) com timestamp e motivo.

## O que NÃO deve ser agente (v1)

- Motor de pontuação ponderada (função determinística).
- Gerador de imagem (API/ferramenta com contrato de execução).
- Redimensionamento, crop e aplicação de copy/logo (compositor determinístico).
- Controle de créditos, autorização e políticas de retry (backend).
- Validação de schema e registro de audit trail (backend).


---

