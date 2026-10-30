# Issue 0045: corte de autenticação para cookies

- ADR primária: [ADR-022](../adr/0022-cookie-auth-provider.md)
- Implementação: [issue #128](https://github.com/labLima/creator-backend/issues/128)
- Dependências: [#126](https://github.com/labLima/creator-backend/issues/126), [#127](https://github.com/labLima/creator-backend/issues/127)

O corte elimina Bearer e tokens no corpo como transportes de sessão. A nova
imagem não possui as flags de transição; o rollback usa a imagem anterior por
uma release, conforme o [guia do SPA](../spa-cookie-auth-migration.md).

## Gates de liberação

- [ ] Sign-off explícito do frontend registrado e vinculado à issue #128.
- [ ] Prazo de depreciação comunicado aos clientes afetados, com evidência
      vinculada à issue #128.
- [ ] Código, testes, CI e todos os critérios da issue #128 comprovados.

Não fechar a issue enquanto esses gates permanecerem pendentes. Service tokens
para clientes não-browser são trabalho futuro, fora do escopo deste corte.

## Contexto de liberação

Segundo o responsável pelo projeto, o aplicativo ainda não foi publicado e não
existe integração com o frontend. Não ha sign-off de frontend nem prazo de
depreciação comunicado a registrar neste momento. Antes da primeira integração
ou liberação, confirmar a compatibilidade do frontend e avaliar a necessidade de
comunicação e prazo com o responsável pelo produto; registrar a decisão e as
evidências na issue #128. Não presumir esses criterios como concluídos.
