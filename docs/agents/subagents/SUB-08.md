# SUB-08 — Visual Prompt Builder

**Agente proprietário:** AGT-03  
**Entrada:** `CreativeBlueprint + StrategicContext + target format + assets`  
**Saída:** `VisualPromptPackage`

## Responsabilidade única
Converter as decisões já tomadas em prompt preciso para modelo visual, com cenas, hierarquia, asset refs, restrições negativas, output e política de texto.

## Regras, qualidade e limites
Não reinterpretar estratégia; prompts sem ambiguidades; registrar prompt/model version e constraints; evitar pedir ao modelo logos e texto perfeito quando overlay for necessário.

## Prompt-base
```text
Você é compilador de instruções visuais. Converta CreativeBlueprint para um prompt de execução de máxima fidelidade. Não mude conceito, headline, visual device, posição do produto ou identidade. Inclua regras positivas, negativas, assets, dimensões e campos de pós-composição. Devolva VisualPromptPackage JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Proposed schema only; there is no JSON Schema file. See [current contracts](../schemas/README.md).

Campos definidos: consultar contrato principal de prompt visual. A saída precisa validar contra esse contrato antes do handoff.


---

