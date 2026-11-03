# Mapa de domínio — proposta × runtime atual

> **Status:** documento de tradução. A coluna "artefato proposto" vem do desenho AGT-01..04/SUB-01..11, que é proposta conceitual e não o contrato ativo. Consulte [schemas/README.md](schemas/README.md) e [agent-specification-compatibility.md](../agent-specification-compatibility.md).

Este mapa evita que nomes da proposta sejam lidos como tipos já implementados. "Equivalente" indica que a responsabilidade hoje é coberta por outro artefato/contrato; "ausente" indica que não há equivalente direto e a capacidade não existe no runtime.

| Artefato proposto | Equivalente atual | Status |
|---|---|---|
| `CreationRequest` | `ImageWorkflowRequest` (`src/creator/workflow/schemas.py`) | Equivalente |
| `CreationRun` | Agent Workflow: runs e steps persistidos por `src/creator/workflow/service.py` | Equivalente |
| `BrandProfile` | Brand + Brand Settings + Brand Knowledge | Equivalente |
| `CampaignBrief` | Campaign | Equivalente |
| `PersonaProfile` | Persona | Equivalente |
| `ProductFacts` | Sem equivalente direto; fatos podem aparecer em Brand Knowledge ou na Campaign com fonte | Ausente |
| `StrategicContext` | `BusinessOutput` | Equivalente |
| `CreativeBlueprint` | Não implementado; mais próximo de `PlannerOutput` + `WriterOutput.direction` | Ausente |
| `VisualPromptPackage` | `WriterOutput.direction.visual_prompt` | Equivalente |
| `ImageAsset` | Content Artifact Type `IMAGE` (`images`) | Equivalente |
| `CreativeQAReport` | `ReviewOutput` / `ImageReviewResult` | Equivalente |

A rubrica ponderada de 0–100, o `CreativeBlueprint` e o compositor determinístico continuam proposta; ver [workflows/QUALITY_SCORE.md](workflows/QUALITY_SCORE.md) e [workflows/IMPLEMENTATION_ROADMAP.md](workflows/IMPLEMENTATION_ROADMAP.md).
