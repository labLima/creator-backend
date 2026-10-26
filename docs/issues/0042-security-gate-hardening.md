# Issue 0042: security gate hardening

- Status: in progress
- ADR primária: [`0010-architecture-governance`](../adr/0010-architecture-governance.md)
- ADR tracker: [`#43`](https://github.com/lefilcompany/creator-backend-python/issues/43)
- Labels: `process`, `quality`, `security`, `ci`

## Objetivo

Restabelecer o security gate da CI na branch `dev` após o `pip-audit` bloquear o job
por vulnerabilidades do Pillow 12.3.0, garantindo que o Gitleaks execute na mesma
execução quando a auditoria de dependências passar.

## Implementação

- Pillow é restringido a `>=13,<14`, removendo a versão vulnerável do conjunto de
  dependências suportado.
- Dependências transitivas com correção publicada recebem limites mínimos seguros
  explícitos: `aiohttp`, `certifi`, `filelock`, `multidict`, `oauthlib`,
  `opentelemetry-api`, `PyJWT` e `urllib3`.
- Os quatro IDs de ChromaDB já existentes (`PYSEC-2026-311`,
  `PYSEC-2026-3813`, `PYSEC-2026-3814` e `PYSEC-2026-3815`) permanecem
  explicitamente identificados no comando de auditoria porque o advisories database
  não informa versão de correção para `chromadb` 1.5.9. A exceção é limitada a esses
  IDs e deve ser removida assim que o upstream publicar uma versão corrigida.
- O job `security` continua falhando em qualquer vulnerabilidade reportada pelo
  `pip-audit` ou secret encontrado pelo Gitleaks.
- O Gitleaks usa `.gitleaks.toml` e checkout completo (`fetch-depth: 0`) no CI, para
  verificar o histórico disponível da execução.

## Critérios de aceite

- [x] `pyproject.toml` exige Pillow `>=13,<14`.
- [x] `make dependency-audit` passa localmente com o ambiente atualizado; o CI deve
  repetir o mesmo alvo no próximo push.
- [ ] Gitleaks executa no CI e não encontra secrets (aguarda o próximo run).
- [ ] O check `Dependency and secret scanning` é obrigatório para merge em `dev`.
- [x] Testes do Gemini image generator, storage e worker passam após o upgrade.

## Limitações externas

A obrigatoriedade de um check para merge é uma configuração de branch protection/ruleset
do GitHub e não é expressa pelo workflow versionado. Deve ser aplicada ao branch `dev`
com o check `Dependency and secret scanning` selecionado como required status check.
