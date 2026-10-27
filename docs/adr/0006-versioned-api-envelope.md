# ADR-006: API versionada com envelope estável

- Status: accepted
- Fonte: `adr_creator_python.pdf`, seção 8
- Tracker: [#39](https://github.com/labLima/creator-backend/issues/39)

## Decisão

Rotas públicas usam `/api/v1`. Sucesso retorna `success`, `data` e `meta.request_id`; falhas retornam `success`, `error.code`, `error.message` e `meta.request_id`.

O mesmo UUID é devolvido no header `X-Request-ID`. Se o cliente não enviar um
UUID válido nesse header, Creator gera um novo identificador. O identificador é
propagado para logs estruturados, Generation Jobs, RQ workers e integrações.
Exceções inesperadas usam o envelope `INTERNAL_ERROR` sem expor detalhes da
exceção.

## Issues vinculadas

#4, #13, #16, #17, #18, #19, #25, #28 e [observabilidade](../issues/0043-observability-correlation.md).
Consulte o [tracker central](../ADR-ISSUE-TRACKER.md).
