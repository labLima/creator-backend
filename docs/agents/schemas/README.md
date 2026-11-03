# Contratos atuais

Este diretório não contém JSON Schemas fictícios. Os contratos vigentes são os modelos Pydantic e envelopes versionados no código:

- Business: `BusinessOutput`.
- Planner: `PlannerOutput`.
- Writer: `WriterOutput`.
- Reviewer: `ReviewOutput`.
- Artist: a geração de imagem usa a boundary `ImageGenerationProvider` e o resultado é `ImageGenerationResult`; `ArtistOutput` é apenas o nome conceitual da proposta, não um contrato ativo.
- Handoffs: contratos tipados em `creator.services.agents.pipeline`.

Os outputs do adapter de kickoff cobrem Business, Planner e Writer. Artist e Reviewer executam por boundaries de Provider próprias, não pelo registry de kickoff.

## Camadas de prompt

| Camada | Versão | Constante / entrypoint | Escopo |
|---|---|---|---|
| Design do agente | `3.0` | `AGENT_DESIGN_VERSION`, `AGENT_DESIGNS` | 5 papéis: title, goal, backstory, task e expected_output. |
| Especificação do especialista | `2.0` | `SPECIALIST_SPEC_VERSION`, `SPECIALIST_SPECS` | 5 papéis: goal, instructions, inputs, output e permitted_tools. |
| Prompt renderizado | `3.0` | `AGENT_PROMPT_VERSION`, `build_agent_prompt` | Compõe design v3 + spec v2; prompt v2 usa apenas a spec v2. |
| Contratos de kickoff | `3.0` | `AGENT_CONTRACTS` | Registry de output schemas apenas para Business, Planner e Writer. |
| Boundary de imagem | `ImageGenerationProvider` | `creator/services/ai/image_provider.py` | Artist executa o Provider; não passa pelo registry. |
| Boundary de revisão | `ReviewOutput` / `ImageReviewResult` | Provider multimodal | Reviewer valida e roteia; não passa pelo registry. |

`AGENT_CONTRACTS` cobre exatamente três papéis (Business, Planner e Writer). Artist e Reviewer não passam pelo registry de kickoff: usam as boundaries de Provider acima. Os hashes golden do prompt v3 são fixados em `tests/test_specialist_specs.py`; qualquer mudança de texto exige bump de versão.

Uma rubrica de nove eixos, score 0–100, limiares e hard blockers permanece proposta em [QUALITY_SCORE.md](../workflows/QUALITY_SCORE.md). O contrato atual do Reviewer usa score de 0–1 e decisões `APPROVED`, `REFINE` e `REJECTED`; nenhuma conversão implícita é válida.

