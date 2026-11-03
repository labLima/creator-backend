# Contratos atuais

Este diretório não contém JSON Schemas fictícios. Os contratos vigentes são os modelos Pydantic e envelopes versionados no código:

- Business: `BusinessOutput`.
- Planner: `PlannerOutput`.
- Writer: `WriterOutput`.
- Reviewer: `ReviewOutput`.
- Artist: a geração de imagem usa a boundary `ImageGenerationProvider`; não existe `ArtistOutput` tipado. O nome `ArtistOutput` em material proposto não é contrato ativo.
- Handoffs: contratos tipados em `creator.services.agents.pipeline`.

Os outputs do adapter de kickoff cobrem Business, Planner e Writer. Artist e Reviewer executam por boundaries de Provider próprias, não pelo registry de kickoff.

Uma rubrica de nove eixos, score 0–100, limiares e hard blockers permanece proposta em [QUALITY_SCORE.md](../workflows/QUALITY_SCORE.md). O contrato atual do Reviewer usa score de 0–1 e decisões `APPROVED`, `REFINE` e `REJECTED`; nenhuma conversão implícita é válida.

