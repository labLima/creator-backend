# ADR-027: Adaptação generativa de imagem para novos formatos

- Status: accepted
- Relacionada: ADR-014, ADR-016, ADR-025 e ADR-026
- Tracker: [#154](https://github.com/labLima/creator-backend/issues/154)
- Implementação: [#155](https://github.com/labLima/creator-backend/issues/155), [#156](https://github.com/labLima/creator-backend/issues/156), [0056](../issues/0056-generative-image-adaptation.md)

## Contexto

O desdobramento de peças adapta um Content IMAGE já existente para outro formato
de publicação. O resultado precisa manter escala percebida, qualidade e
coerência com o Creative Concept e o Brand Context. Crop ou resize geométrico
isolado não resolve essa necessidade.

Creator já modela transformação IMAGE como operação `TRANSFORM` de Generation
Job e aceita `source_content_id`. A lacuna é a edição dos pixels da imagem
existente e os parâmetros de destino. Edição generativa precisa receber os
bytes da origem escolhida, e não só uma descrição textual. A origem não pode ser
sobrescrita; texto, logos e outros elementos que exigem fidelidade exata não
podem ser alterados silenciosamente pelo Provider.

A funcionalidade existente no Creator do Lovable é referência de comportamento.
Esta decisão e suas issues cobrem a API, Generation Job, storage e Provider
deste repositório, sem trabalho de interface ou mudanças no Lovable.

## Decisão

Uma imagem enviada pelo Principal pode originar um Content IMAGE e sua primeira
Content Version, vinculados a um Brand autorizado. Os bytes são validados e
armazenados de forma imutável; a versão importada não representa uma Generation
e não possui model ou prompt de provider. O mesmo TRANSFORM aceita a versão
importada ou uma versão gerada, mantendo a autorização e a revisão humana.
O fluxo de importação é rastreado em [#160](https://github.com/labLima/creator-backend/issues/160)
e [0057](../issues/0057-image-import.md).

Estender `IMAGE/TRANSFORM` existente. A origem é uma Content Version IMAGE
específica, não apenas o Content corrente: antes de enfileirar, a aplicação
autoriza o Content e a versão no Workspace e Brand da Generation e resolve os
bytes imutáveis dessa versão. O cliente não fornece URL de origem. O adapter
recebe os bytes ou uma referência interna opaca que só o backend consegue
resolver. Se a versão exata não estiver disponível, a solicitação falha.

Na primeira entrega, os destinos permitidos são 1080×1080, 1080×1350,
1080×1920 e 1920×1080. A aplicação registra as dimensões resolvidas no
Generation e valida MIME type suportado, dimensões e proporção da saída antes
de persistir ou liberar o resultado. Uma saída divergente é inválida e não pode
ser corrigida com crop/resize silencioso.

O adapter OpenAI solicita a resolução compatível mais próxima, múltipla de 16,
requisito do endpoint para dimensões customizadas. Depois da edição generativa,
normaliza as dimensões finais para o preset por reamostragem LANCZOS sem corte
e registra ambas as dimensões. Quando a proporção variar, a escala não uniforme
pode introduzir distorção discreta; a Human Review verifica o resultado. Essa
etapa introduz interpolação e não pode substituir a edição generativa.

A capability Provider-neutral recebe bytes da origem, direção/contexto
autorizado e destino, e retorna bytes de imagem com metadados verificáveis.
Edição generativa precisa usar a imagem fonte para expandir ou reorganizar a
composição. Geração apenas textual e transformações geométricas isoladas não
satisfazem o contrato. SDKs de fornecedor permanecem no adapter. A origem não é
alterada; a saída aprovada é uma Variation persistida como nova Content Version
do mesmo Content e vinculada à versão de origem.

Toda Variation fica privada e pendente de Human Review antes de ser liberada.
Texto aprovado e Brand Assets exatos devem ser aplicados pela composição
determinística da ADR-026 quando os dados e assets autorizados estiverem
disponíveis. A edição generativa não recebe garantia de preservar texto, logos
ou outros elementos pixel a pixel. A revisão verifica esses elementos, escala
percebida, continuidade, cortes indesejados e coerência com Creative Concept e
Brand Context. Resultado duvidoso permanece pendente; resultado que falha nos
critérios é rejeitado. Não há crop silencioso. Rejeição e falha disparam limpeza
do artefato privado, com nova tentativa de limpeza para falhas transitórias.

Retries são limitados, idempotentes e pertencem ao ciclo de vida do Generation
Job. A mesma chave e solicitação não podem persistir versões duplicadas; erros
permanentes e saída inválida encerram a tentativa com erro sanitizado. Bytes,
URLs assinadas e credenciais não entram em logs. Provider, model, parâmetros,
dimensões e referências/hash da origem e saída ficam registrados para
rastreabilidade.

Destinos fora dos quatro presets exigem decisão posterior. Fidelidade visual
depende do Provider e da imagem de origem; revisão humana reduz risco, mas não
garante recuperação de conteúdo que o modelo não preservou. A qualidade será
avaliada com fixtures de referência em proporções distintas, testes
determinísticos de formato/dimensões/proporção e checklist visual de escala,
continuidade, cortes e coerência.

Esta decisão não cria preço ou regra comercial de Credits. Deve-se aplicar a
política existente quando houver integração para Generation: no estado atual,
o fluxo de Generation Job não debita Credits nem registra Provider Usage. A
instrumentação desses registros permanece uma lacuna explícita, sem impedir a
adaptação em si e sem ser presumida como entregue.

## Consequências

- A edição generativa fica atrás de interface Provider-neutral, e os contratos
  HTTP/OpenAPI evoluem antes da ativação do comportamento.
- A revisão humana é uma condição de liberação; não constitui garantia técnica
  de preservação exata pelo Provider.
- A saída cria uma nova Content Version imutável do Content de origem e mantém
  vínculo rastreável com a versão escolhida.
- A qualidade e a fidelidade variam com Provider e origem. A saída inválida,
  rejeitada ou impossível de adaptar não é corrigida por crop silencioso.
- O adapter OpenAI pode reamostrar a saída sem crop para cumprir dimensões exatas
  que não sejam múltiplas de 16; a pequena deformação potencial passa pela
  Human Review.
- O fluxo atual de Generation Job não debita Credits nem registra Provider
  Usage; a instrumentação permanece fora desta entrega.
