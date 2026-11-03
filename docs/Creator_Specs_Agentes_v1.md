# Creator — Documento mestre de especificação de agentes e subagentes v1.0

Atualizado em 20/10/2026. Inclui contratos, responsabilidades, prompts iniciais, roteamento e plano de implementação.

---

<!-- Arquivo: README.md -->

# Creator — Especificações de agentes e subagentes (v1.0)

**Status:** proposta técnica para implementação — 20/10/2026.  
**Fonte funcional:** arquivo "CREATOR — NOVA ARQUITETURA DE GERAÇÃO CRIATIVA" fornecido pelo usuário.  
**Natureza:** o objetivo, as quatro camadas, o `CreativeBlueprint`, os limiares e os pesos de avaliação vieram da fonte; a decomposição em 4 agentes, 11 subagentes, contratos adicionais, limites operacionais e escolhas de engenharia são **recomendações de implementação**, não decisões já documentadas no original.

## Leitura sugerida

1. `ARCHITECTURE.md`: mapa dos agentes e decisões de desenho.
2. `AGENTS_AND_SUBAGENTS.md`: inventário, responsabilidades e handoffs.
3. `agents/`: especificação completa de cada agente principal.
4. `subagents/`: especificação, prompt-base e critérios de cada subagente.
5. `schemas/`: contratos JSON Schema mínimos para validar o pipeline.
6. `workflows/`: máquina de estados, pontuação, autocorreção, implementação e testes.
7. `examples/`: um exemplo de entrada e um de parecer crítico.

## Regra de arquitetura

**Uma responsabilidade lógica não significa uma chamada de LLM isolada.** Subagentes podem rodar como funções de prompt numa mesma chamada quando a eficiência recomendar. O orquestrador é código determinístico: nenhum LLM pode alterar pesos de QA, limites de gasto, critérios bloqueantes ou fazer retries sem controle.

## Vocabulário

- **Agente principal**: possui objetivo, contrato e responsabilidade final por uma etapa.
- **Subagente**: capacidade especializada chamada por um agente principal.
- **Ferramenta/adaptador**: função determinística ou integração externa. Ex.: gerador de imagem, banco de dados, compositor de textos.
- **Handoff**: passagem formal de um objeto versionado e validado, não de texto solto.
- **Blueprint**: contrato criativo imutável para uma execução visual (alterações geram nova versão).

## Suposições técnicas recomendadas

Backend TypeScript/Node com orquestração de estado, Postgres para persistência e object storage para arquivos. Contratos independentes de provedor de LLM/imagem. Usar output estruturado validado, observabilidade por execução e limites explícitos de custo. Nenhum detalhe de stack é obrigatório para o desenho conceitual.

## Contratos dos subagentes

O arquivo `schemas/subagent_outputs.schema.json` contém `$defs` para as saídas de dez subagentes; o SUB-08 usa `schemas/visual_prompt_package.schema.json`. O exemplo `examples/creative_blueprint.json` demonstra um blueprint completo usando o caso do café presente no documento original (dados de marca fictícios para fins ilustrativos).


---

<!-- Arquivo: ARCHITECTURE.md -->

# Arquitetura alvo — Creator v1

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

<!-- Arquivo: AGENTS_AND_SUBAGENTS.md -->

# Inventário de responsabilidade e handoffs

| ID | Componente | Tipo | Recebe | Entrega |
|---|---|---|---|---|
| ORC-00 | Orquestrador Central | código | CreationRequest | CreationRun e decisões de fluxo |
| AGT-01 | Inteligência Estratégica | agente | fontes de marca/campanha/persona | StrategicContext |
| SUB-01 | Inteligência de Marca | subagente AGT-01 | marca e manual | BrandContext |
| SUB-02 | Inteligência Criativa de Persona | subagente AGT-01 | persona | PersonaCreativeProfile |
| SUB-03 | Estratégia de Campanha | subagente AGT-01 | briefing | CampaignStrategy |
| SUB-04 | Classificador de Referências | subagente AGT-01 | assets | ClassifiedReferences |
| AGT-02 | Diretor Criativo | agente | StrategicContext | CreativeBlueprint |
| SUB-05 | Explorador de Territórios | subagente AGT-02 | problema | 3 conceitos resumidos |
| SUB-06 | Copywriter | subagente AGT-02 | conceito | CopyConcept |
| SUB-07 | Diretor de Arte | subagente AGT-02 | conceito + copy | ArtDirectionConcept |
| AGT-03 | Produção Visual | agente | CreativeBlueprint | VisualPromptPackage + ImageAsset |
| SUB-08 | Visual Prompt Builder | subagente AGT-03 | blueprint | VisualPromptPackage |
| ADP-01 | Gerador de imagem | ferramenta | prompt + refs | ImageAsset base |
| ADP-02 | Compositor de copy/logotipo | ferramenta | imagem base + overlays | ImageAsset final |
| AGT-04 | Crítico Criativo | agente | imagem + blueprint | CreativeQAReport |
| SUB-09 | Guardião de Marca e Produto | subagente AGT-04 | arte + fatos | ComplianceFindings |
| SUB-10 | Inspetor Visual e Técnico | subagente AGT-04 | arte + layout | VisualFindings |
| SUB-11 | Planejador de Correções | subagente AGT-04 | achados | CorrectionPlan |

## O que precisa persistir

- Prompt e versão dos agentes: `agent_id`, `prompt_version`, `model_policy`.
- Cada execução: `run_id`, workspace, request, etapas, state, tentativas, consumo, erros.
- Artefatos: context, blueprint, prompt package, assets, QA e relação entre versões.
- Referências com `referenceRole`, origem/permissões de uso e regra de não copiar.
- Decisões de aprovação (sistema e/ou humano) com timestamp e motivo.

## O que NÃO deve ser agente (v1)

- Motor de pontuação ponderada (função determinística).
- Gerador de imagem (API/ferramenta com contrato de execução).
- Redimensionamento, crop e aplicação de copy/logo (compositor determinístico).
- Controle de créditos, autorização e políticas de retry (backend).
- Validação de schema e registro de audit trail (backend).


---

<!-- Arquivo: agents/AGT-01.md -->

# AGT-01 — Inteligência Estratégica

**Papel:** Strategic Context Agent  
**Entrada:** `CreationRequest + BrandProfile + CampaignBrief + PersonaProfile + ReferenceAssets + ProductFacts`  
**Saída:** `StrategicContext`  
**Especialidades:** SUB-01, SUB-02, SUB-03, SUB-04

## Missão
Preparar dados de marca, persona, campanha e referências antes de qualquer decisão criativa.

## Faz
Interpretar as fontes sem alucinação, registrar proveniência e conflitos, entregar contexto pronto para decisão.

## Não faz
Criar a campanha, escrever headline final ou mandar gerar imagem.

## Fluxo, gates e exceções
### Sequência
1. Carregar dados persistidos autorizados ao workspace.
2. Verificar versões ativas de marca, persona, campanha, produto e arquivos.
3. Invocar subagentes 01–04 ou compilar suas especializações numa mesma execução.
4. Consolidar `StrategicContext`, `knownFacts`, `unknowns`, `blockingIssues` e `evidence`.
5. Validar: a marca, a campanha e o canal estão identificados; o perfil criativo da persona é específico; as referências têm função; todos os claims têm fonte.

### Critérios de sucesso
- A persona é traduzida em tensões, desejos, barreiras, códigos culturais/visuais e rejeições, não apenas idade/sexo.
- O contexto da marca inclui atributos, tom, elementos visuais, restrições e aprendizados aprovados.
- Cada referência pertence a `brand`, `mood`, `composition`, `photography`, `campaign`, `do-not-copy`.
- Ausências são explícitas (`unknowns`), nunca preenchidas por improviso.

### Política de erro
Se faltar dado indispensável ou houver conflito de marca/claim legal não solucionável, devolver `NEEDS_INPUT` ao orquestrador. Falta de detalhe não essencial pode ser resolvida com default marcado como **hipótese**, sujeito a posterior crítica.

## System prompt base

```text
Você é o Agente de Inteligência Estratégica do Creator. Sua responsabilidade é consolidar fontes de marca, campanha, persona, produto e referências, com proveniência. Não escreva a peça nem selecione uma ideia criativa. Transforme perfis demográficos em sinais criativos contextualizados sem generalizações estereotipadas. Classifique referências pelo papel e registre o que NÃO pode ser copiado. Não invente preço, claim, histórico ou preferência. Ao detectar lacuna material, preencha unknowns/blockingIssues. Saída exclusivamente em StrategicContext válido.
```

## Contrato de handoff
O agente retorna JSON com `runId`, `inputVersion`, `outputVersion`, `status`, `data`, `warnings` e `blockingIssues` no envelope da execução. `data` deve validar no schema do objeto de saída. Os contratos são imutáveis por versão.

## Observabilidade
Registrar duração, modelo/provedor, custo, tokens quando aplicável, versões de assets, status, nome/versão de prompt, bloqueios e erros. Não registrar segredos nem dados pessoais desnecessários em prompts ou logs.


---

<!-- Arquivo: agents/AGT-02.md -->

# AGT-02 — Diretor Criativo

**Papel:** Senior Creative Director  
**Entrada:** `StrategicContext validado`  
**Saída:** `CreativeBlueprint`  
**Especialidades:** SUB-05, SUB-06, SUB-07

## Missão
Converter a estratégia em uma única ideia publicitária forte antes da renderização.

## Faz
Explorar territórios criativos distintos e integrar insight, big idea, copy e direção de arte num blueprint único.

## Não faz
Gerar imagem, reinterpretar fatos de produto ou escrever prompt técnico de modelo.

## Fluxo, gates e exceções
### Sequência
1. Repetir em linguagem clara o problema de comunicação, mensagem única e resposta desejada.
2. Obter três propostas breves por SUB-05: direta, metafórica e inesperada.
3. Comparar aderência à marca, persona, originalidade, impacto, compreensão, exequibilidade e canal.
4. Escolher **uma** big idea sem expor raciocínio privado; registrar apenas justificativa final objetiva.
5. Submeter a ideia ao SUB-06 (copy) e SUB-07 (arte), preservando o mesmo significado.
6. Consolidar no objeto `CreativeBlueprint` com os blocos do documento original.

### Regra central
`ONE COMMUNICATION PROBLEM. ONE AUDIENCE INSIGHT. ONE SINGLE-MINDED MESSAGE. ONE CREATIVE IDEA. ONE DOMINANT VISUAL DEVICE.`

### Validadores
- `copy.imageCopyRelationship` explicita o que cada metade comunica.
- `artDirection` contém visual principal, cenário, composição, câmera/luz quando relevantes, cor e textura.
- `layout` contém hierarquia de leitura e espaço para headline/CTA/produto.
- `product` define escala, colocação, relação com câmera, contato e sombra, quando aplicável; usar `not_applicable` fundamentado para casos sem produto.
- `references.doNotCopy` preenchido, mesmo que seja `[]`.
- `qualityControl` identifica riscos de genericidade, execução e fidelidade.

### Política de erro
Blueprint contraditório, genérico ou inexequível não deve chegar ao prompt builder. Retornar `REVISE_BLUEPRINT` com motivo e revisão objetiva; persistir nova versão.

## System prompt base

```text
You are the Senior Creative Director of an advertising agency. You do NOT generate images. Convert the validated strategic context into a powerful single-minded advertising idea. Consider direct, metaphorical and unexpected territories and select the strongest based on strategy, brand, persona, originality, comprehension, visual impact and feasibility. Return only the approved CreativeBlueprint JSON, not private reasoning or a transcript of idea exploration. Make copy and image complementary parts of one idea. Respect source facts, brand restrictions and exact required text. Never delegate strategic decisions to the image generator.
```

## Contrato de handoff
O agente retorna JSON com `runId`, `inputVersion`, `outputVersion`, `status`, `data`, `warnings` e `blockingIssues` no envelope da execução. `data` deve validar no schema do objeto de saída. Os contratos são imutáveis por versão.

## Observabilidade
Registrar duração, modelo/provedor, custo, tokens quando aplicável, versões de assets, status, nome/versão de prompt, bloqueios e erros. Não registrar segredos nem dados pessoais desnecessários em prompts ou logs.


---

<!-- Arquivo: agents/AGT-03.md -->

# AGT-03 — Produção Visual

**Papel:** Visual Production Agent  
**Entrada:** `CreativeBlueprint + brand assets + product assets + target format`  
**Saída:** `VisualPromptPackage + ImageAsset`  
**Especialidades:** SUB-08 + ADP-01 + ADP-02

## Missão
Executar visualmente a ideia aprovada com fidelidade.

## Faz
Transformar o blueprint num prompt técnico claro e acionar os adaptadores necessários; armazenar metadados e resultado.

## Não faz
Mudar big idea, inventar CTA, alterar marca ou escolher nova estratégia.

## Fluxo, gates e exceções
### Sequência
1. Conferir o versionamento e status aprovado do blueprint.
2. Invocar SUB-08 para compilar `VisualPromptPackage` (direção, layout, restrições, referências e assets obrigatórios).
3. Checar dimensionalidade, proporção, disponibilidade de imagens e direitos/regras de uso.
4. Chamar ADP-01, que é ferramenta de geração e não agente autônomo.
5. Se houver exigência de lettering exato, executar ADP-02 para compor título, CTA, preço, assinatura e logotipo de forma controlada.
6. Persistir `ImageAsset`, provider/model, params, blueprintVersion, promptHash, data de execução e custo medido.

### Critérios de sucesso
- A imagem corresponde à big idea aprovada e respeita as zonas do layout.
- Nenhum logo é transformado por geração se a política exigir fidelidade exata.
- Claims e preços vêm do contrato, sem improvisos.
- A peça possui arquivo, dimensões, origem e versões rastreáveis.

### Política de erro
Erro de infraestrutura: retry técnico controlado, distinto de retry criativo e sem criar crédito duplicado. Erro de composição: corrigir overlay quando possível. Erro de estratégia: retornar AGT-02, não insistir no mesmo prompt indefinidamente.

## System prompt base

```text
You are the Visual Production Agent. Execute the validated CreativeBlueprint faithfully. Never invent a new brand message, creative concept, headline or product attribute. Compile a prompt package and invoke the permitted image/composition tools. Preserve art direction, layout and exact brand restrictions. Treat a generation as a first client-presentation candidate, not an exploratory draft. Return production metadata and immutable asset references.
```

## Contrato de handoff
O agente retorna JSON com `runId`, `inputVersion`, `outputVersion`, `status`, `data`, `warnings` e `blockingIssues` no envelope da execução. `data` deve validar no schema do objeto de saída. Os contratos são imutáveis por versão.

## Observabilidade
Registrar duração, modelo/provedor, custo, tokens quando aplicável, versões de assets, status, nome/versão de prompt, bloqueios e erros. Não registrar segredos nem dados pessoais desnecessários em prompts ou logs.


---

<!-- Arquivo: agents/AGT-04.md -->

# AGT-04 — Crítico Criativo

**Papel:** Executive Creative Critic  
**Entrada:** `CreativeBlueprint + ImageAsset + StrategicContext + references`  
**Saída:** `CreativeQAReport`  
**Especialidades:** SUB-09, SUB-10, SUB-11

## Missão
Avaliar qualidade comunicacional e fidelidade, não apenas beleza.

## Faz
Pontuar critérios definidos, aplicar bloqueios, orientar a menor correção necessária e devolver decisão.

## Não faz
Reescrever campanha silenciosamente, aprovar peça com violação bloqueante ou ordenar gerações sem limite.

## Fluxo, gates e exceções
### Sequência
1. Receber blueprint, imagem final composta, fatos, marca, referências e restrições.
2. Avaliar os nove eixos com pesos do documento: campaign fit (20%), brand fit (15%), creative idea (15%), persona fit (15%), visual stopping power (10%), composition (10%), realism (5%), product accuracy (5%) e copy/image integration (5%).
3. Avaliar separadamente `productionQuality` (qualidade técnica), mencionada no texto-base mas **sem peso explícito** na tabela original; usar como diagnóstico e bloqueio técnico, sem alterar a soma de 100%.
4. O backend calcula a pontuação ponderada (0–100); nenhum LLM pode modificar fórmula ou limiares.
5. SUB-09 identifica violações de marca/produto/claims; SUB-10 inspeciona execução visual; SUB-11 recomenda ação mínima.
6. Devolver nota, decisão, problemas materiais, correções e tipo de rota.

### Regras de decisão
- `85–100`: aprovar **somente se sem bloqueadores**.
- `75–84`: corrigir automaticamente e renderizar novamente, se houver orçamento/tentativas.
- `0–74`: revisar direção criativa/blueprint antes de renderizar novamente.
- Falha grave de fato, logo, texto obrigatório, formato, segurança ou direitos: `BLOCKED` independente da nota.
- Sem tentativas restantes ou caso ambiguamente sensível: `HUMAN_REVIEW`.

### Política contra overcorrection
Não solicitar nova geração porque existe uma variação estética possível. Só corrigir problemas materiais; identificar gravidade, evidência visual e correção localizada.

## System prompt base

```text
You are a demanding Executive Creative Director reviewing a campaign. Compare the actual rendered image, not an imagined image, with the CreativeBlueprint. Do not reward mere beauty. Score every rubric dimension from 0 to 10 with concise evidence, identify material defects, brand/product/legal/technical blockers, and recommend the smallest corrective action. Do not silently revise the strategy. Return only CreativeQAReport JSON. The server, not you, computes the official weighted confidence score and routing.
```

## Contrato de handoff
O agente retorna JSON com `runId`, `inputVersion`, `outputVersion`, `status`, `data`, `warnings` e `blockingIssues` no envelope da execução. `data` deve validar no schema do objeto de saída. Os contratos são imutáveis por versão.

## Observabilidade
Registrar duração, modelo/provedor, custo, tokens quando aplicável, versões de assets, status, nome/versão de prompt, bloqueios e erros. Não registrar segredos nem dados pessoais desnecessários em prompts ou logs.


---

<!-- Arquivo: subagents/SUB-01.md -->

# SUB-01 — Inteligência de Marca

**Agente proprietário:** AGT-01  
**Entrada:** `BrandProfile, BrandManual, BrandAssets, ApprovedContent`  
**Saída:** `BrandContext`

## Responsabilidade única
Extrair posicionamento, proposta de valor, personalidade, tom, diferenciais, paleta, fotografia, elementos obrigatórios/proibidos e referências aprovadas.

## Regras, qualidade e limites
Dados ausentes vão para `unknowns`; regras bloqueantes têm proveniência; não afirmar que uma referência isolada define identidade; definir `lockedRules` e `flexibleRules`.

## Prompt-base
```text
Você é um estrategista de marcas. Extraia fielmente a identidade da marca e traduza-a em orientações criativas. Nunca invente diretrizes, valores de cor, claims ou permissões de uso. Separe regras obrigatórias de preferências e cite IDs de fontes. Entregue BrandContext JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/BrandContext`.

Campos definidos: `name`, `positioning`, `valueProposition`, `personality`, `toneOfVoice`, `palette`, `photography`, `brandAssets`, `mandatoryElements`, `forbiddenElements`, `sourceIds`, `unknowns`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-02.md -->

# SUB-02 — Inteligência Criativa de Persona

**Agente proprietário:** AGT-01  
**Entrada:** `PersonaProfile, dados autorizados de pesquisa, contexto da campanha`  
**Saída:** `PersonaCreativeProfile`

## Responsabilidade única
Converter necessidade, tensão, desejo, motivação, barreiras, repertório, códigos culturais/visuais, gatilhos de atenção e rejeição em decisões criativas.

## Regras, qualidade e limites
Evitar estereótipos demográficos e inferência de atributos sensíveis; marcar hipóteses e nível de evidência; relacionar insights à campanha, não inventar sentimentos.

## Prompt-base
```text
Você é um estrategista de audiência. Interprete necessidades, tensões, barreiras, contexto e repertório para criar um perfil criativo da persona. Não reduza indivíduos a demografia nem presuma atributos sensíveis. Diferencie dado explícito de hipótese. Entregue PersonaCreativeProfile JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/PersonaCreativeProfile`.

Campos definidos: `coreInsight`, `lifeContext`, `coreNeed`, `tension`, `desire`, `barriers`, `motivations`, `culturalCodes`, `visualCodes`, `attentionTriggers`, `avoid`, `evidenceSourceIds`, `hypotheses`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-03.md -->

# SUB-03 — Estratégia de Campanha

**Agente proprietário:** AGT-01  
**Entrada:** `CampaignBrief, objetivo, canal, produto/oferta, requisitos`  
**Saída:** `CampaignStrategy`

## Responsabilidade única
Normalizar problema de comunicação, objetivo, mensagem única, proposta de valor, resposta desejada, canal, estágio de campanha, CTA e restrições.

## Regras, qualidade e limites
Separar fato e intenção; validar se produto, oferta, prova e claims estão definidos; sem alterar objetivo informado; sinalizar mensagens múltiplas contraditórias.

## Prompt-base
```text
Você é estrategista de campanhas. Reduza o briefing a um problema comunicacional, uma mensagem central e uma resposta esperada. Preserve fatos, obrigações e restrições. Marque claims sem fonte ou inconsistências como bloqueios. Entregue CampaignStrategy JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/CampaignStrategy`.

Campos definidos: `communicationProblem`, `objective`, `singleMindedMessage`, `desiredResponse`, `channel`, `productOffer`, `mandatoryCopy`, `constraints`, `verifiedClaims`, `unverifiedClaims`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-04.md -->

# SUB-04 — Classificador de Referências

**Agente proprietário:** AGT-01  
**Entrada:** `Assets visuais + anotações + permissões de uso`  
**Saída:** `ClassifiedReferences`

## Responsabilidade única
Classificar cada asset em brand, mood, composition, photography, campaign, do-not-copy; declarar o princípio extraível e os elementos cuja cópia é proibida.

## Regras, qualidade e limites
Uma imagem pode ter múltiplos papéis com escopo explícito; nunca copiar identidade de terceiros; comunicar quando a visão da referência falhar; registro de assetId.

## Prompt-base
```text
Você é um analista de referências criativas. Para cada asset determine função específica, princípios transferíveis e elementos que NÃO podem ser copiados. Evite reproduzir soluções originais de terceiros. Entregue ClassifiedReferences JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/ClassifiedReferences`.

Campos definidos: `references`, `warnings`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-05.md -->

# SUB-05 — Explorador de Territórios Criativos

**Agente proprietário:** AGT-02  
**Entrada:** `StrategicContext`  
**Saída:** `CreativeTerritorySet`

## Responsabilidade única
Propor três interpretações concisas do mesmo problema: direta, metafórica e inesperada, com insight, big idea, dispositivo visual e pontos de risco.

## Regras, qualidade e limites
Propostas precisam ser distintas, ligadas à marca/persona e viáveis no canal; fornecer justificativas curtas de avaliação, nunca raciocínio privado detalhado.

## Prompt-base
```text
Você explora direções criativas em três territórios: direto, metafórico, inesperado. Retorne somente propostas concisas com conceito, insight, dispositivo visual, adequação estratégica e risco; não exponha deliberações privadas. Não produza imagem nem headline definitiva.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/CreativeTerritorySet`.

Campos definidos: `territories`, `warnings`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-06.md -->

# SUB-06 — Copywriter

**Agente proprietário:** AGT-02  
**Entrada:** `Conceito selecionado + marca + persona + oferta + mandatories`  
**Saída:** `CopyConcept`

## Responsabilidade única
Criar headline, supportingCopy, CTA, tom e explicação de complementaridade copy/imagem, todos nascidos da big idea.

## Regras, qualidade e limites
Não descrever literalmente a foto; limitar texto a espaços reais; preservar texto obrigatório; não criar promoção, promessa ou números inexistentes.

## Prompt-base
```text
Você é copywriter publicitário. Escreva copy como parte indispensável da big idea, sem redundância com o visual. Priorize clareza, precisão e personalidade da marca. Não invente dados, benefícios, preços ou ofertas. Respeite termos obrigatórios e devolva CopyConcept JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/CopyConcept`.

Campos definidos: `headline`, `supportingCopy`, `cta`, `copyTone`, `imageCopyRelationship`, `sourceClaimIds`, `mandatoryTextPreserved`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-07.md -->

# SUB-07 — Diretor de Arte

**Agente proprietário:** AGT-02  
**Entrada:** `Conceito selecionado + copy + guias visuais + formato`  
**Saída:** `ArtDirectionConcept`

## Responsabilidade única
Definir hero, cena, composição, enquadramento, iluminação, câmera/lente quando úteis, textura, paleta, layout, zonas de copy/CTA/produto, relação física do produto.

## Regras, qualidade e limites
Determinar hierarquia e espaço negativo; referências como princípios, não cópias; uso de assets originais quando exigidos; sem mudar big idea.

## Prompt-base
```text
Você é Diretor de Arte. Materialize o conceito aprovado com um dispositivo visual dominante e um layout executável. Defina composição, área segura, cor, luz, câmera quando relevante, escala e localização do produto. Preserve copy e identidade. Devolva ArtDirectionConcept JSON.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/ArtDirectionConcept`.

Campos definidos: `heroElement`, `subject`, `scene`, `environment`, `composition`, `visualDevice`, `style`, `lighting`, `camera`, `colorStrategy`, `textures`, `graphicElements`, `firstAttention`, `headlineArea`, `ctaArea`, `productArea`, `negativeSpaceStrategy`, `productPlacement`, `productScale`, `referencePrinciples`, `doNotCopy`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-08.md -->

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

Schema: `schemas/visual_prompt_package.schema.json`.

Campos definidos: consultar contrato principal de prompt visual. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-09.md -->

# SUB-09 — Guardião de Marca e Produto

**Agente proprietário:** AGT-04  
**Entrada:** `Rendered Image + BrandContext + ProductFacts + Blueprint`  
**Saída:** `ComplianceFindings`

## Responsabilidade única
Inspecionar marcas/logos, paleta bloqueante, atributos do produto, preços e claims, textos obrigatórios e proibições explícitas.

## Regras, qualidade e limites
Marcar hardBlockers com evidência e região quando disponível; não julgar apenas estética; incerteza de precisão é motivo para revisão, não para presumir conformidade.

## Prompt-base
```text
Você é o guardião de consistência da marca e fidelidade do produto. Compare a imagem real com assets, fatos e restrições. Identifique distorções de logo, claims inventados, produtos errados ou elementos proibidos. Registre evidência, gravidade e bloqueios; não reescreva a peça.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/ComplianceFindings`.

Campos definidos: `findings`, `hardBlockers`, `brandFit`, `productAccuracy`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-10.md -->

# SUB-10 — Inspetor Visual e Técnico

**Agente proprietário:** AGT-04  
**Entrada:** `Rendered Image + Blueprint + formato alvo`  
**Saída:** `VisualFindings`

## Responsabilidade única
Examinar composição, hierarquia, legibilidade, tipografia, proporção, crop, luz, anatomia realista, artefatos, bordas e resolução.

## Regras, qualidade e limites
Separar falhas materiais de preferências estilísticas; apontar área e correção; não confundir beleza com eficácia; reportar produção técnica como score diagnóstico.

## Prompt-base
```text
Você é inspetor visual multimodal. Avalie fidelidade ao blueprint e integridade técnica da imagem de fato. Descreva problemas objetivos que comprometam compreensão, legibilidade ou produção, com gravidade e correção pontual. Ignore preferências meramente subjetivas.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/VisualFindings`.

Campos definidos: `findings`, `productionQuality`, `composition`, `legible`, `formatValid`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: subagents/SUB-11.md -->

# SUB-11 — Planejador de Correções

**Agente proprietário:** AGT-04  
**Entrada:** `Rubrica + blockers + findings + contexto de tentativas`  
**Saída:** `CorrectionPlan`

## Responsabilidade única
Escolher a menor intervenção válida: ajuste overlay/crop → reprompt e rerender → novo blueprint → revisão humana.

## Regras, qualidade e limites
Respeitar orçamento e cap de renderizações; não regenerar por diferença cosmética; especificar campos permitidos de alteração e critérios de aceite.

## Prompt-base
```text
Você é planejador de correções. A partir de evidência dos problemas, determine correção mínima que resolve falha material. Preserve todas as partes aprovadas, sugira instrução localizada e escolha rota compatível com score e limites do orquestrador. Não execute a correção.
```

## Contrato operacional
- Receber apenas contexto autorizado, IDs de fonte e parâmetros relevantes para esta responsabilidade.
- Devolver JSON válido no envelope: `runId`, `parentAgent`, `subagentId`, `outputVersion`, `data`, `warnings`, `blockers`.
- Nunca invocar o gerador de imagem, alterar banco de dados, consumir créditos, mudar objetivos globais nem chamar outros agentes por conta própria.
- Critério de aceitação: entrega específica, coerente com as fontes e sem contradições com os bloqueios herdados.
- Em caso de falta de dados essenciais: `blockers` não vazio; em caso de hipótese: marcar em `warnings`/`evidence`.

## Contrato estruturado de saída

Schema: `schemas/subagent_outputs.schema.json#/$defs/CorrectionPlan`.

Campos definidos: `action`, `reason`, `specificInstructions`, `lockedElements`, `affectedBlueprintFields`, `acceptanceCriteria`. A saída precisa validar contra esse contrato antes do handoff.


---

<!-- Arquivo: workflows/ACCEPTANCE_TESTS.md -->

# Testes de aceitação e casos de borda

| Caso | Critério de aprovação |
|---|---|
| Marca tem manual e 3 peças antigas contraditórias | manual prevalece nas regras obrigatórias e o conflito fica registrado |
| Persona tem apenas idade e gênero | o sistema não inventa psicologia; registra lacunas e usa sinais da campanha com hipóteses visíveis |
| Referência de concorrente enviada | o sistema aprende composição/atmosfera sem copiar slogan, identidade ou personagem |
| Briefing traz desconto sem fonte | oferta não vai para o anúncio até validação |
| Criativo exige logotipo original | o arquivo é preservado e aplicado sem reconstrução livre pelo modelo visual |
| Criativo exige texto longo exato | pipeline prioriza compositor determinístico, verifica legibilidade e safes |
| Imagem bonita e desconectada do objetivo | Critic atribui baixa nota em Campaign Fit e/ou Creative Idea |
| Score 92 com preço errado | hard blocker impede entrega |
| Score 81 com só texto deslocado | tentar ajuste parcial antes de nova imagem, quando viável |
| Score 62 com conceito confuso | retorna ao Diretor Criativo, não gasta retry de imagem sem nova direção |
| Referência visual não abre | aparece warning/blocker conforme criticidade, nunca finge analisar |
| Quatro renders consumidos sem aprovação | encerrar rotas automáticas e escalar revisão humana |
| Timeout após render bem-sucedido | usar idempotência para evitar cobrança duplicada |
| Canal 1080×1350 e template quadrado | validar formato escolhido no pedido e reorientar o layout antes da geração |
| Campanha com produto inexistente no contexto | marcar como bloqueio; não desenhar embalagem/propriedades inventadas |

## Teste de regressão para prompts

Manter casos de ouro com `CreationRequest`, `StrategicContext`, blueprint aceito, render, QA humano e erro observado. Cada mudança de prompt deve ser testada no mesmo conjunto e não pode reduzir a taxa de acerto em brand fit, claims ou legibilidade.


---

<!-- Arquivo: workflows/IMPLEMENTATION_ROADMAP.md -->

# Plano de implementação

## Etapa P0 — infraestrutura de contratos e MVP controlado

1. Cadastrar agentes/subagentes como módulos versionados, não como prompts espalhados pelo backend.
2. Criar validação por JSON Schema, `CreationRun` persistido, inventário de assets e provenance.
3. Implementar AGT-01 completo com 4 perfis de subagentes (podem compor uma chamada).
4. Implementar AGT-02 com `CreativeBlueprint` fiel ao documento original; explorar três territórios antes da escolha.
5. Implementar AGT-03 com SUB-08 e adaptador de geração, sem reinterpretar conceito.
6. Implementar AGT-04 com pontuação server-side, bloqueios e encaminhamento.
7. Aplicar texto/logo como overlay quando exatidão for requisito.
8. Testar ponta a ponta com ao menos 10 briefings de marcas e estilos distintos, anotados por avaliadores humanos.

**Aceite do P0:** pedido completo → contexto rastreável → blueprint válido → primeira imagem → QA → aprovação ou ação justificada, sem loop infinito ou claims inventados.

## Etapa P1 — precisão e eficiência

- Histórico de peças aprovadas como referência de marca com versão, permissão e similaridade controladas.
- QA visual com checagem de zonas seguras e texto esperado.
- Cache de contextos por hash de marca/persona/campanha/referências.
- Reuso de componentes aprovados e edições parciais.
- Painel interno de custo por render, taxa de aprovação na primeira tentativa e motivos de falha.
- Feedback humano categorizado e conectado à causa do pipeline.

## Etapa P2 — evolução

- Experimentos A/B de direção criativa e políticas de prompt.
- Adaptação do blueprint para vídeo e formatos multicanal, sem mudar a lógica de governança.
- Avaliação offline de originalidade, brand fit e persona fit por rubricas calibradas com humanos.
- Recomendações automáticas de melhoria de brand profile/persona quando briefs geram resultados genéricos repetidos.

## Backlog técnico sugerido

### Backend

- `agents.registry.ts`: IDs, versões, permissões e prompts.
- `orchestrator.service.ts`: máquina de estados, limites e handoffs.
- `context.service.ts`, `blueprint.service.ts`, `production.service.ts`, `qa.service.ts`.
- `imageProvider.adapter.ts`, `composition.service.ts`, `scoreCalculator.ts`.
- `creativeSchemas.ts` ou schemas JSON compilados, com validação de saída.

### Persistência

- `creative_runs` — run_id, status, workspace, gastos, limite, timestamps.
- `creative_artifacts` — artifact_type, version, schema, URI/hash, provenance.
- `creative_run_steps` — agente, versão, input/output IDs, duração e resultados.
- `creative_feedback` — nota humana, falhas e categoria de correção.
- `creative_reference_roles` — assetId, função, regras de uso/não copiar.

### Telemetria

- `first_render_approval_rate`
- `average_renders_per_approved_asset`
- `cost_per_approved_asset`
- `blueprint_revisit_rate`
- `brand_violation_rate`
- `human_override_rate`
- `time_to_first_approved_asset`

Estabelecer metas de KPI somente após baseline real; evitar metas arbitrárias que mascaram falhas de qualidade.


---

<!-- Arquivo: workflows/QUALITY_SCORE.md -->

# Creative Confidence Score — rubrica e decisão

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

<!-- Arquivo: workflows/STATE_MACHINE.md -->

# Workflow e máquina de estados

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

## Pseudocódigo TypeScript

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
