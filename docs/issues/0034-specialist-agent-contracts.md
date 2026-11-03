# Issue 0034: specialist agent contracts, prompts and RAG

- ADR: [`0014-agent-image-generation-workflow`](../adr/0014-agent-image-generation-workflow.md)
- Labels: `agents`, `provider`, `implementation`
- GitHub: [#58](https://github.com/labLima/creator-backend/issues/58)

## Scope

Implementar schemas e prompts versionados para Business, Planner, Writer, Artist e Reviewer, com outputs JSON validados, hash dos inputs e contexto de Brand/BrandSettings/RAG escopado por Workspace.

O documento [Creator Specs Agentes v1](../Creator_Specs_Agentes_v1.md) propõe quatro
agentes e onze especialidades. A adaptação dos prompts aos contratos atuais e seus limites
estão descritos em [agent-specification-compatibility](../agent-specification-compatibility.md).
Os contratos de `CreativeBlueprint`, QA ponderado e composição determinística ainda não
foram implementados; não considerar os critérios abaixo como aceite dessas capacidades.

## Acceptance criteria

- [x] Nenhum raciocínio interno é persistido ou exposto.
- [x] Prompt rendering é determinístico e possui testes golden.
- [x] Output inválido não alcança Content, Generation ou Image.
- [x] RAG indisponível usa somente o contexto persistido e registra a fonte utilizada.
