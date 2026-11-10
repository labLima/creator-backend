# ADR-028: Referências visuais autorizadas para o Artist

- Status: accepted
- Relacionada: ADR-002, ADR-014, ADR-025, ADR-026 e ADR-027
- Tracker: [#148](https://github.com/labLima/creator-backend/issues/148)
- Relacionada: #78 (qualidade e observabilidade de geração)

## Contexto

O Artist recebe contexto principalmente textual. A seleção explícita de imagens
de referência ajuda a reproduzir identidade visual, embalagem e ambiente, mas
bytes e URLs fornecidos pelo cliente não demonstram propriedade ou autorização.

## Decisão

Referências são Assets privados vinculados ao Workspace e à Brand autorizada.
Um endpoint autenticado valida PNG, JPEG ou WebP, tamanho máximo de 10 MiB,
dimensões e assinatura real do conteúdo; gera o caminho de storage e persiste
checksum SHA-256 e marca de origem controlada pelo servidor. A API aceita uma
lista ordenada de até quatro IDs nos Generation Jobs IMAGE e Agent Workflows.

O boundary de aplicação valida Workspace, Brand, lifecycle e origem segura ao
enfileirar. O worker repete a autorização e valida tamanho, formato, dimensões e
hash antes de cada chamada ao Provider. TRANSFORM envia primeiro a versão fonte
e depois as referências. Storage ou Provider indisponível encerra a tentativa;
não existe fallback silencioso sem referências. Integrações seguem atrás das
interfaces provider-neutral. Logs guardam IDs e hashes, nunca bytes ou URLs.

## Consequências

O OpenAPI inclui upload e IDs de referência. A lista vazia mantém o fluxo atual.
Assets cadastrados por URLs ou caminhos de cliente não são elegíveis. Mudanças,
remoção ou indisponibilidade antes da execução falham com erro sanitizado.
