# ADR-027: Adaptação generativa de imagem para novos formatos

- Status: proposed
- Relacionada: ADR-014, ADR-016, ADR-025 e ADR-026
- Tracker: [#154](https://github.com/labLima/creator-backend/issues/154)
- Implementação: [#155](https://github.com/labLima/creator-backend/issues/155), [#156](https://github.com/labLima/creator-backend/issues/156), [0056](../issues/0056-generative-image-adaptation.md)

## Contexto

O desdobramento de peças adapta um Content IMAGE já existente para outro formato
de publicação. O resultado precisa manter escala percebida, qualidade e
coerência com o Creative Concept e o Brand Context. Um crop ou resize geométrico
não resolve essa necessidade porque pode eliminar conteúdo ou deixar áreas sem
composição.

Creator já modela transformação como operação de Generation e dispõe de
Generation Jobs IMAGE. A capacidade nova precisa usar edição generativa sem
acoplar a aplicação a um fornecedor e sem sobrescrever o Content de origem.
Texto, logos e outros elementos que exigem fidelidade exata também não podem ser
alterados silenciosamente pelo Provider.

## Decisão proposta

Representar o desdobramento como Generation de operação `TRANSFORM` e Artifact
Type `IMAGE`, executada por Generation Job. A edição generativa deve expandir ou
reorganizar a imagem para cumprir as dimensões/proporção de destino; crop/resize
convencional isolado não é o resultado da funcionalidade.

A saída é uma Variation e uma nova Content Version imutável, relacionada ao
Content/Content Version de origem. O Generation registra a referência de origem,
dimensões/proporção de origem e destino, Provider/model e parâmetros necessários
para rastreabilidade. A origem permanece intacta.

A integração de edição de imagem fica atrás de uma interface Provider-neutral.
Autorização da fonte e do Brand Context ocorre na fronteira da aplicação, com
validação de Workspace, ownership, MIME type, tamanho e dimensões. Texto, logos
e Brand Assets que exijam precisão devem ser preservados por estratégia
determinística ou encaminhados a revisão humana conforme os limites de confiança
do Provider e a ADR-026.

Os contratos HTTP e `docs/openapi.yaml` devem ser atualizados antes de ativar ou
alterar comportamento da API. Retry precisa ser seguro e respeitar a
idempotência e o ciclo de vida do Generation Job.

## Consequências

- A transformação pode ser assíncrona e consumir recursos/créditos de Provider;
  custo e limites devem ficar explícitos no fluxo de Generation.
- Qualidade e fidelidade visual variam por Provider e imagem de origem; a
  capacidade deve registrar parâmetros e aplicar revisão quando necessário.
- A nova versão não altera nem substitui a origem e precisa manter vínculo
  rastreável com ela.
- O escopo, as dimensões aceitas, a origem permitida e o tratamento de elementos
  exatos ainda precisam ser confirmados antes de marcar esta ADR como aceita.
