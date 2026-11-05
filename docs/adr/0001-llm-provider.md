# ADR-001: Abstração de provider de LLM

- Status: accepted
- Fonte: `adr_creator_python.pdf`, seção 3
- Tracker: [#34](https://github.com/labLima/creator-backend/issues/34)

## Contexto

Creator precisa gerar texto sem acoplar o domínio a um fornecedor.

## Decisão

O domínio depende de provider interfaces; OpenAI é o provider ativo para geração de texto e imagem. O adapter de texto usa a Responses API e o adapter de imagem usa Images API. A seleção ocorre em factories e credenciais ficam fora do código. Gemini permanece apenas como integração opcional para capacidades existentes de embeddings e revisão multimodal, não como provider padrão de geração.

A composição de prompts é uma boundary de aplicação separada dos endpoints e dos providers. Templates são versionados e renderizados de forma determinística antes de chamar o provider; o identificador, versão e hash da entrada acompanham a Generation para observabilidade.

## Consequências

Trocar o vendor não exige alterar endpoints ou casos de uso. O adapter não configurado falha explicitamente, evitando geração falsa em produção.

## Issues vinculadas

#3, #9, #11, #13 (adapter original, substituído para geração), [#17](../issues/0017-prompt-templates.md), [#19](../issues/0019-sync-text-content-generation.md), #23, #27 e [#143](https://github.com/labLima/creator-backend/issues/143) / [0053](../issues/0053-openai-provider-migration.md). Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
