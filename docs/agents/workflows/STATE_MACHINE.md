# Workflow e máquina de estados

> **Proposta, não máquina de estados ativa.** A máquina ativa e os retries são do Creator e estão definidos em ADR-014/018 e no worker Python.

```text
RECEIVED
  ↓ VALIDATING_INPUT → NEEDS_INPUT (em caso de bloqueio)
CONTEXT_BUILDING
  ↓ CONTEXT_READY
BLUEPRINT_BUILDING
  ↓ BLUEPRINT_VALIDATING → REVISE_BLUEPRINT (se falhar)
BLUEPRINT_READY
  ↓ PROMPT_BUILDING
RENDERING
  ↓ COMPOSITING (quando copy/logo exatos)
QUALITY_REVIEW
  ├── score >= 85 e sem bloqueios → APPROVED → DELIVERED
  ├── 75 <= score < 85 → REPAIR_PLAN → RENDERING
  ├── score < 75 → REVISE_BLUEPRINT → BLUEPRINT_BUILDING
  ├── qualquer hard blocker → BLOCKED / REPAIR_PLAN / HUMAN_REVIEW
  └── limite/erro irrecuperável → HUMAN_REVIEW ou FAILED
```

## Retry policy recomendada (nova decisão técnica)

- Máximo de 4 renderizações por solicitação (`maxRenders=4`), **configurável** por plano; a fonte original não determina um limite.
- Máximo de 2 revisões de blueprint (`maxBlueprintRevisions=2`).
- Nunca repetir exatamente o mesmo prompt sem mudança material; exceção: erro comprovado de infraestrutura.
- `score>=85`: não regenerar, salvo blocker.
- `75..84`: no máximo uma etapa de correção localizada antes de novo QA; repetir enquanto houver tentativas e a falha tiver mudado.
- `score<75`: novo blueprint/versionamento, antes de consumir outra renderização.
- `BLOCKED`: ver natureza do problema; se claim ou direito não verificável, pausar para revisão humana; se mero artefato técnico corrigível, reparar.
- Se não houver caminho permitido, devolver ao usuário resultado e explicação operacional, sem fingir aprovação.

## Pseudocódigo ilustrativo (não executável; não representa o stack do Creator)

```ts
async function createContent(request: CreationRequest) {
  const run = await createRun(request);
  const context = await strategicAgent.build(request);
  assertContextGate(context);
  let blueprint = await creativeDirector.build(context);

  for (let revision = 0; revision <= run.policy.maxBlueprintRevisions; revision++) {
    assertBlueprintGate(blueprint);
    while (run.renderCount < run.policy.maxRenders) {
      const prompt = await promptBuilder.compile(blueprint, context);
      const imageBase = await imageProvider.generate(prompt);
      const imageFinal = await composer.applyRequiredOverlays(imageBase, prompt);
      run.renderCount++;
      const review = await critic.evaluate({context, blueprint, imageFinal});
      review.score = calculateScore(review.criteria); // backend
      if (review.hardBlockers.length === 0 && review.score >= 85) {
        return deliver(imageFinal, review);
      }
      const plan = routeAndPlan(review, run.policy); // backend owns routing
      if (plan.action === 'REPAIR_RENDER') { /* new prompt version */ continue; }
      if (plan.action === 'REVISE_BLUEPRINT') break;
      return requestHumanReview(run, review);
    }
    if (revision === run.policy.maxBlueprintRevisions) break;
    blueprint = await creativeDirector.revise({context, blueprint, lastReview: run.lastReview});
  }
  return requestHumanReview(run, run.lastReview);
}
```

Este pseudocódigo é ilustrativo; a implementação real precisa persistir estado após cada fronteira, isolar idempotência, processar callbacks/job IDs de provedores e distinguir falha técnica de revisão criativa.

## Falhas a testar

- JSON fora do schema → refazer apenas saída estruturada, sem render.
- Ausência de fonte para claim → revisão humana/entrada adicional.
- Duas referências com estilos incompatíveis → pedir decisão ou aplicar prioridade explicitamente validada.
- Modelo de imagem devolve output sem asset → retry técnico com chave idempotente.
- Render duplicado por timeout → não cobrar nem armazenar duplamente.
- Texto/CTA/valor ilegível → overlay/ajuste localizado antes de geração inteira.
- Confiança alta com logo distorcido → blocker prevalece.

