# ADR-029: ciclo limitado de Automated Review para IMAGE independente

- Status: accepted
- Tracker: [#167](https://github.com/labLima/creator-backend/issues/167)
- Implementação: [#168](https://github.com/labLima/creator-backend/issues/168)
- Relacionadas: ADR-025, ADR-026, issue [#78](https://github.com/labLima/creator-backend/issues/78)

## Contexto

IMAGE Generation Jobs independentes podem solicitar Automated Review. Até aqui,
o REVIEWER registrava a avaliação opcional, mas uma decisão `REFINE` não
produzia outra tentativa. Cortes, enquadramento, inconsistência espacial e texto
inesperado podiam chegar ao Content sem correção automática.

## Decisão

Quando `review_image` está ativo, o worker avalia cada candidato contra o
Briefing, Brand Context, proporção e enquadramento, objetos cortados,
consistência espacial e texto inesperado. `REFINE` exige feedback acionável e
cria outra tentativa com essa correção, mantendo o prompt aprovado e o Creative
Concept. `image_review_max_attempts` limita o total de avaliações e aceita
valores de 1 a 10. O prompt v6 do REVIEWER mantém os controles de v5 e adiciona
os critérios de qualidade visual e de correção acionável. O feedback retornado
é limitado, tratado como dado não confiável e não pode alterar o conceito ou o
Brand Context aprovados.

Somente o candidato terminal é persistido como Content Version pelo Generation
Job e Workspace originais. O Reviewer pode terminar em `APPROVED`, `REJECTED`,
`exhausted` ou `failed`; o worker registra também as tentativas, falhas,
provedor/modelo, latência e custo estimado quando fornecido pelo Provider. Uma
recusa do Provider continua sendo falha estruturada do Generation Job segundo
as regras existentes. A aprovação automatizada nunca substitui Human Review,
Approval ou a decisão humana exigida pela política do Content.

Quando o Provider não expõe custo, configurações unitárias opcionais
`IMAGE_GENERATION_COST_ESTIMATE_USD` e `IMAGE_REVIEW_COST_ESTIMATE_USD`
permitem estimar custo por chamada; sem elas, a telemetria registra `null`.

## Consequências

- O limite é configuração do servidor; não muda o contrato HTTP nem a política
  de aprovação humana.
- Cada tentativa usa a autorização e o Workspace do Generation Job original;
  não aceita identificadores de Workspace vindos do Reviewer.
- A telemetria de tentativa complementa a avaliação e observabilidade de #78.
- Jobs sem `review_image` mantêm o fluxo atual.
