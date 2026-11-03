# Matriz de compatibilidade — legado Create Bloom 73 → Creator atual

- Fonte: `docs/migration/legacy-inventory.md`
- Snapshot do legado: `main` @ `1dd4b416111ea97de9b3e3395f04823760aea018`
- Backend atual: `dev` @ `108fb09`
- Status: **inventário de código concluído; migração de comportamento e ETL pendentes**
- Regra: `Equivalente` exige contrato + dados + comportamento; `Parcial` tem endpoint/modelo, mas falta comportamento/campo; `Ausente` não tem equivalente; `Novo` não é paridade legada.

| # | Comportamento legado | Evidência legada | Backend atual | Status | Lacuna principal |
|---:|---|---|---|---|---|
| 1 | Login por senha/sessão | `src/routes/auth.tsx`, Supabase Auth | `/auth/login` + cookies | Parcial | sem confirmação de e-mail/OTP/OAuth; hash local Argon2 incompatível |
| 2 | Cadastro/onboarding | `auth.tsx`, `checkout.tsx` | `/auth/signup` | Parcial | sem confirmação, checkout/onboarding e plano inicial |
| 3 | Recuperação de senha/OTP/magic link | `password-reset.functions.ts`, `login-code.functions.ts`, `auth-emails.functions.ts` | ausente | **Ausente** | nenhum endpoint de reset/OTP/magic link |
| 4 | Google OAuth | `src/integrations/lovable`, `auth.tsx` | ausente | **Ausente** | sem provider OAuth |
| 5 | Importação/migração de usuários | `import-users.functions.ts` | ausente | **Ausente** | sem import, convite de senha ou status de migração |
| 6 | Perfil do usuário | `app.profile.tsx` | `/users/me`, `/settings` | Parcial | phone/city/state, preferências de UI e metadata ausentes |
| 7 | CRUD de workspace | `v2_create/update/delete_workspace` | `/workspaces` | Parcial | sem slug, owner, plano, metadata |
| 8 | Equipe, papéis e convites | `TeamView.tsx`, `workspace-settings.tsx`, RPCs `v2_*` | `/workspace-invites` CRUD | Parcial | sem aceite, troca de role, remoção, leave, team payload |
| 9 | Feature flags/limites do workspace | `workspace_settings`, `FeaturesTab` | ausente | **Ausente** | sem `allow_*`, limites mensais, `max_posts_per_calendar` |
| 10 | CRUD de marca | `BrandsView.tsx`, `v2_upsert_brands` | `/brands`, `/brands/{id}/settings` | Parcial | listas, assets, logo/moodboard/training, JSON completo |
| 11 | Importação/treino/RAG de marca | `brand-import`, `brand-web`, `brand-knowledge`, `RagIndexControl` | ausente/stub | **Ausente** | sem upload/import, brand knowledge, training, embeddings |
| 12 | Temas/editorias | `ThemesView.tsx`, `v2.campaigns` | `/campaigns` | Parcial | colisão semântica; sem brand_id/metadata/hashtags/voices/expected_action |
| 13 | Personas | `PersonasView.tsx`, `v2.personas` | `/personas` | Parcial | campos e limites muito menores; sem interesses/foto/cidade/detalhes |
| 14 | Planejamento/calendário | `CalendarPanel.tsx`, `content_plans` | `/planning` | Parcial | sem nome/metadata/items/datas estruturadas; campaign/persona obrigatórios |
| 15 | Posts, captions e design | `posts/captions/post_designs/design_slides` | `/post-structures`, `/design-structures` | Parcial | sem briefing/design brief/captions/aprovação/slides; `design_structure` vazio |
| 16 | Geração de calendário por IA | `generateCalendarPosts` | ausente | **Ausente** | nenhum endpoint equivalente |
| 17 | Copy, direções e design brief | `copy.functions`, `content-directions.functions`, `design-brief.functions` | `/content/generate`, `/content/improve` | Parcial | geração genérica, não por post/calendário/marca |
| 18 | Geração/composição de imagem | `design.functions`, `image-creator.functions`, `carousel.functions`, `image-refine.functions`, `resize.functions` | `/images/generate`, `/generations/image-workflows` | Parcial | sem composição de marca, overlay, carrossel, refino, resize |
| 19 | QA/revisão/aprovação | `agt04-critic`, `reviewCreation`, feedback | `/generations/image-workflows/{id}/decision` | Parcial | sem QA report persistido, aprovação/rejeição e histórico de versões |
| 20 | Histórico/atividade | `activity_log`, `v2_history_page`, `HistoryView` | `/contents`, `/generations` | Parcial | sem activity log nem endpoint de histórico |
| 21 | Vídeo | `video.functions`, `video30.functions`, tabelas de vídeo | ausente | **Ausente** | nenhum modelo/endpoint de vídeo |
| 22 | Feed/comunidade | `feed_*`, `publishedFeed.ts`, `FeedView.tsx` | ausente | **Ausente** | nenhum modelo/endpoint de feed/stories |
| 23 | Créditos/wallet/lots | `credits.ts`, `spend_credits`, `workspace_credit_lots` | `/workspace-credit-transactions` CRUD | Parcial | sem saldo, lotes, expiração, consumo, free allowance |
| 24 | Billing/checkout/assinatura | `payments.functions`, Pagar.me | `/plans`, `/orders`, `/subscriptions` CRUD | Parcial | sem provider/checkout/webhook; schema insuficiente |
| 25 | Cupons/descontos | `coupons`, `redeem_coupon`, `previewDiscountCoupon` | `/coupons`, `/coupon-redemptions` CRUD | Parcial | sem aplicação, resgate ou regra once-per-workspace |
| 26 | Webhooks/reconciliação Pagar.me | rotas `/api/public/pagarme-*` | ausente | **Ausente** | sem endpoint público nem adapter |
| 27 | Notificações/e-mail | Resend, `feed_notifications`, preferences | `/notifications` CRUD | Parcial | sem envio/entrega/push/email |
| 28 | Admin/backoffice | `admin.functions`, `admin-insights.functions` | `/users` admin | **Ausente** | sem métricas, relatórios, catálogo, webhooks, Redis, busca |
| 29 | Assets/upload/signed URLs | `mediaUpload.ts`, `brand-assets`, `signAssetUrls` | `/assets` metadata CRUD | Parcial | sem upload nem assinatura em lote |
| 30 | Health/metrics | não existia | `/health`, `/metrics` | **Novo** | comportamento novo, não legado |
| 31 | Projects | não existia | `/projects` | **Novo** | modelo transitório do backend atual |
| 32 | Landing/legal/sitemap/frontend | rotas públicas da SPA | n/a | **Fora de escopo** | frontend, não backend |

**Contagem:** 0 equivalentes, 19 parciais, 10 ausentes, 3 novos/fora de escopo.

---

