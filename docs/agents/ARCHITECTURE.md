# Arquitetura alvo — Creator v1

> **Proposta, não fluxo implementado.** O fluxo canônico implementado é Business → Planner → Writer → Artist → Reviewer → DELIVERY, conforme ADR-014/017/018. Os gates e artefatos abaixo não substituem os contratos ativos. A rubrica de QA é apenas proposta; veja [contratos atuais](schemas/README.md).

## Objetivo de produto

Transformar uma solicitação em uma **peça publicitária planejada antes de ser renderizada**. Fluxo canônico:

`Solicitação → Contexto de marca/campanha/persona/referências → Diretor Criativo → Creative Blueprint → Copy + Arte → Prompt visual → Geração → Crítico Criativo → Decisão`.

O gerador de imagem não deve criar estratégia, headline, proposta de valor ou big idea. Ele executa o blueprint.

## Organograma

```text
ORC-00  ORQUESTRADOR CENTRAL (código; não LLM)
  |
  +-- AGT-01 INTELIGÊNCIA ESTRATÉGICA
  |     SUB-01 Inteligência de marca
  |     SUB-02 Inteligência criativa de persona
  |     SUB-03 Estratégia de campanha
  |     SUB-04 Classificação de referências
  |     entrega: StrategicContext
  |
  +-- AGT-02 DIRETOR CRIATIVO
  |     SUB-05 Exploração de territórios criativos
  |     SUB-06 Copywriter
  |     SUB-07 Diretor de arte
  |     entrega: CreativeBlueprint
  |
  +-- AGT-03 PRODUÇÃO VISUAL
  |     SUB-08 Visual Prompt Builder
  |     ADP-01 Modelo gerador de imagem (ferramenta, não agente)
  |     ADP-02 Compositor/overlay (quando necessário)
  |     entrega: VisualPromptPackage + ImageAsset
  |
  +-- AGT-04 CRÍTICO CRIATIVO
        SUB-09 Guardião de marca e produto
        SUB-10 Inspetor visual e técnico
        SUB-11 Planejador de correções
        entrega: CreativeQAReport
```

## Definição clara de agentes vs. subagentes

- **Agente** controla uma fase, reúne resultados de suas especialidades, assume responsabilidade sobre uma entrega, e responde ao orquestrador.
- **Subagente** executa uma função limitada, não altera contratos globais e não chama diretamente outro estágio.
- **Adaptador** recebe parâmetros definidos, aciona serviços de renderização/composição e retorna artefatos, sem autonomia criativa.

## Dados e sua precedência

1. `BrandProfile`/manual ativo: identidade, marca registrada, paleta, logos, elementos proibidos.
2. `CampaignBrief` ativo: objetivo, oferta, CTA, linguagem exigida, exigências e restrições — desde que não violem restrições obrigatórias da marca.
3. `ProductFacts` com fonte verificável: preço, características, embalagem, SKU e declarações factuais.
4. `PersonaProfile` e insumos relevantes do público.
5. Referências classificadas conforme sua função.
6. Conteúdos anteriores aprovados e defaults do Creator.

Conflito material deve entrar em `unknowns`/`blockingIssues`. Nunca resolver inventando. O usuário pode solicitar exceção à identidade, mas a exceção precisa estar registrada explicitamente e só pode sobrepor regras não bloqueantes.

## Artefatos versionados

- `CreationRequest` — pedido de criação.
- `StrategicContext` — interpretação consolidada com evidências.
- `CreativeBlueprint` — proposta aprovada pelo sistema ou por humano quando exigido.
- `VisualPromptPackage` — contrato de execução do modelo visual.
- `ImageAsset` — imagem renderizada e/ou composta.
- `CreativeQAReport` — notas, problemas, bloqueios e instrução de correção.
- `CreationRun` — estado de execução, custos, versões e eventos.

Usar IDs e hashes/versionamentos para saber exatamente qual versão do contexto produziu qual imagem.

## Gates

1. **Gate contextual:** entradas mínimas presentes, informação material sem contradição insolúvel.
2. **Gate de conceito:** o blueprint tem uma ideia única, copy/arte coerentes, restrições respeitadas e é executável.
3. **Gate pré-render:** prompt não altera a estratégia; dimensões, assets e texto exato conferidos.
4. **Gate pós-render:** score e bloqueios definidos no QA.

## Pipeline de custo eficiente (v1)

Chamada 1: AGT-01 consolida os subagentes 01–04 (visão apenas se houver referência).  
Chamada 2: AGT-02 idealiza três alternativas breves, escolhe uma e integra subagentes 05–07 em um blueprint único (podem ser chamadas separadas em tarefas complexas).  
Chamada 3: SUB-08 compila um prompt de execução.  
Ferramenta: gerador de imagem (1 render inicialmente).  
Chamada 4: AGT-04 faz revisão multimodal com checagens 09–11.  
Apenas quando necessário: uma ou mais revisões limitadas pelo orquestrador.

## Política de texto e logo

O campo `copy.headline` do blueprint é conteúdo, não uma autorização para o modelo visual inventar tipografia. Quando o produto exigir grafia 100% exata e logo intacto, preferir **renderizar a base visual sem lettering final** e aplicar texto/logos como camadas determinísticas. A aplicação de overlays deve obedecer a posições, área segura e layout já definidos. Modelos de imagem podem falhar em texto ou fidelidade de logotipo; não prometer exatidão sem validação.

## Fronteiras de responsabilidade

- O crítico não reescreve objetivo nem muda big idea silenciosamente.
- O prompt builder não cria nova copy.
- A direção de arte não modifica claims de produto.
- O copywriter não inventa benefícios, provas ou preços.
- O planejador de correção escolhe o **menor nível de intervenção** necessário: overlay/crop → reprompt → nova renderização → novo blueprint → revisão humana.


---

