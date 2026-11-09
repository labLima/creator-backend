# ADR-026: Composição determinística de imagem publicitária

- Status: accepted
- Relacionada: ADR-014, ADR-016, ADR-025 e issue #78
- Tracker: [#152](https://github.com/labLima/creator-backend/issues/152)
- Implementação: [#147](https://github.com/labLima/creator-backend/issues/147), [0054](../issues/0054-deterministic-image-composition.md)

## Contexto

Prompts de imagem tentam gerar cena, marca e texto em uma única etapa. Isso
dificulta garantir ortografia, alinhamento e margens. Generation Jobs IMAGE e
Agent Workflow já persistem seus resultados como artefatos imutáveis.

## Decisão proposta

Composição é opt-in e recebe manchete, apoio e CTA explicitamente aprovados.
O provider gera apenas a cena; uma camada determinística aplica texto e marca
com assets autorizados do Brand Context. A cena passa por detecção de texto;
resultados positivos impedem entrega e resultados inconclusivos exigem revisão
humana. A camada de composição preserva dimensões e enquadramento, não altera o
texto aprovado e falha quando fonte, marca ou espaço seguro não estão válidos.

No Generation Job IMAGE independente, a cena inconclusiva fica no storage privado
e o Job permanece `PROCESSING` com `scene_review.status=PENDING` nos parâmetros.
O endpoint autenticado de decisão expõe URL temporária para inspeção; aprovar
retoma o mesmo Job com a cena armazenada, e rejeitar encerra o Job. Jobs à espera
não são reclamados pelo worker nem pelo recuperador de processamento obsoleto.
Ao rejeitar, o caminho entra em limpeza pendente; a API tenta excluir o objeto
imediatamente e o worker repete a exclusão a cada cinco minutos em caso de falha
transitória. A conclusão fica registrada nos parâmetros do Generation.

As versões dos prompts e da composição, fontes e demais assets, dimensões e
parâmetros ficam nos metadados do Generated Image. A detecção não garante
ausência absoluta de texto e deve ser tratada como controle de risco.

## Consequências

Os contratos HTTP e `docs/openapi.yaml` devem evoluir antes da ativação dos
workers. A implementação requer interfaces provider-neutral para detecção,
resolução segura de Brand Assets e testes de formato e layout. O opt-in mantém
compatibilidade das solicitações existentes.
