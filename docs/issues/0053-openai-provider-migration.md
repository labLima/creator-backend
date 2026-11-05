# 0053 — OpenAI como provider ativo de geração

- Status: implementação em andamento
- ADR primária: [ADR-001](../adr/0001-llm-provider.md)
- Issue tracker: [#34](https://github.com/labLima/creator-backend/issues/34)
- Issue de implementação GitHub: [#143](https://github.com/labLima/creator-backend/issues/143)

## Objetivo

Usar OpenAI para geração de texto, imagem e revisão multimodal atrás das
interfaces de provider já existentes, incluindo geração de imagem a partir de
um Post Structure pertencente a um Planning.

## Critérios de aceite

- [ ] `OPENAI_API_KEY` configura o `LLMProvider`, o `ImageGenerator` e o reviewer.
- [ ] OpenAI Images API devolve bytes e metadados normalizados para persistência.
- [ ] Generation Job pode receber Planning e Post Structure, validar acesso e
  montar briefing/direção com os dados da peça.
- [ ] Content e resposta do Generation Job preservam os IDs de Planning e Post Structure.
- [ ] Erros de autenticação, quota, timeout, bloqueio e resposta inválida são
  classificados sem expor a chave nem o corpo sensível do provider.
- [ ] Gemini deixa de ser selecionado como provider padrão de geração de texto e
  imagem.
- [ ] Configuração, documentação e evidência de qualidade são atualizadas.
