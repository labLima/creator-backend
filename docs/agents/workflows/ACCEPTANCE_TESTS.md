# Testes de aceitação e casos de borda

> **Não implementado.** Casos de aceitação da proposta; o contrato atual está em [schemas/README.md](../schemas/README.md).

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

