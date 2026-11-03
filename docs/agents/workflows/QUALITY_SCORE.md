# Creative Confidence Score — rubrica e decisão

> **Não implementado.** A rubrica abaixo descreve uma proposta. O runtime atual valida `ReviewOutput.score` entre 0 e 1 e aceita as decisões `APPROVED`, `REFINE` e `REJECTED`; não calcula os nove eixos, thresholds 85/75 nem hard blockers server-side.

## Base fiel ao documento de origem

| Critério | Peso |
|---|---:|
| Campaign Fit | 20% |
| Brand Fit | 15% |
| Creative Idea | 15% |
| Persona Fit | 15% |
| Visual Stopping Power | 10% |
| Composition | 10% |
| Realism | 5% |
| Product Accuracy | 5% |
| Copy/Image Integration | 5% |
| **Total** | **100%** |

**Fórmula** (cada critério recebe nota de 0 a 10):

`score = Σ(notaCritério × pesoPercentual) ÷ 10`

A nota final vai de 0 a 100. Exemplo: todas as notas iguais a 9 geram score 90.

O texto original também manda avaliar `Production Quality`, mas não lhe atribui peso na seção de pesos. Decisão recomendada nesta v1: medir de 0 a 10 como **diagnóstico**, com falhas técnicas críticas como bloqueadores. Não incluí-lo no score para não alterar os pesos definidos.

## Política de aprovação

- 85–100: `APPROVE` se nenhum bloqueador material.
- 75–84: `REPAIR_RENDER` com correção mínima e QA subsequente.
- 0–74: `REVISE_BLUEPRINT` antes de nova geração.
- Um `hardBlocker` sempre impede aprovação mesmo acima de 85.
- Orçamento/tentativas esgotados → `HUMAN_REVIEW`.

## Hard blockers sugeridos

1. Logo ou produto visualmente incorreto em situação de exigência exata.
2. Claim, preço, desconto, EAN ou dado de produto inventado/incorreto.
3. Elemento explicitamente proibido no BrandContext.
4. Conteúdo obrigatório ausente ou ilegível.
5. Formato/dimensões ilegais para a entrega.
6. Uso de material sem permissão quando a validação de direitos for obrigatória.
7. Violação de regra de segurança ou conformidade aplicável.

Bloqueios são regras do produto a validar e aprovar em política; nem todos precisam ser acionados em todos os casos.

## Pontuação operacional

O AGT-04 propõe notas individuais, com evidências; **o backend calcula `score` e `decision`**. Se o parecer não trouxer evidência suficientemente concreta para um bloqueio, ele vai para revisão humana ou para uma checagem específica, jamais aprovação silenciosa.


---

