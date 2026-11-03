# Inventário de migração — Create Bloom 73 → Creator backend

> **Artefato de inventário.** snapshot do legado analisado estaticamente; não há
> dump de dados/storage. A matriz de comportamento está em
> [`legacy-compatibility-matrix.md`](legacy-compatibility-matrix.md).

## Snapshot analisado

| Item | Valor |
|---|---|
| Legado | `/tmp/opencode/create-bloom-73` |
| Branch/commit | `main`, `1dd4b416111ea97de9b3e3395f04823760aea018` (2026-10-30, clone raso) |
| Backend atual | `/home/emanueljtrodrigues/Documents/LeFil/creator-backend` |
| Branch/commit | `feat/milestone-3-foundation`, `108fb09b230d387aa917c2014925bf186ddb1982` (2026-11-03) |
| Método | Leitura estática de código, migrations, OpenAPI e testes; nenhuma migration/teste executado; nenhum segredo lido |
| Limitação | O clone legado é code-only: não há dump do banco, contagens de linhas, amostras ou export de storage |

Definições usadas no texto:

```text
LEGACY  = /tmp/opencode/create-bloom-73
CURRENT = /home/emanueljtrodrigues/Documents/LeFil/creator-backend
```

---

## 1. Veredito executivo

1. **O legado não é um backend REST.** É uma SPA TanStack Start com Supabase. Grande parte do “backend” está em `createServerFn` (RPCs internos), funções RPC do PostgREST (`/rest/v1/rpc/...`) e acesso direto a tabelas/views com RLS.
2. **Inventário quantificado:** 104 server functions de produto (+1 demo), 4 handlers HTTP públicos, 106 RPCs distintas do Supabase, 32 views expostas, ~70 tabelas ativas e 5 buckets de storage.
3. **Contagem de rotas:** 108 handlers de aplicação (104 server functions + 4 HTTP públicos); **214 endpoints endereçáveis** se os 106 RPCs forem contados. Incluindo sitemap/demo chega-se a 216 handlers.
4. **Equivalência:** nenhum comportamento foi classificado como plenamente equivalente. Na matriz: **0 equivalentes, 19 parciais, 10 ausentes, 3 novos/fora de escopo**.
5. **Principais bloqueios:** autenticação (recuperação/OTP/OAuth/importação), billing/Pagar.me, créditos, pipeline calendário→copy→design, fidelidade da geração de imagem, vídeo, feed, workspace/equipe e dados legados em JSON (`creator_state`/`extra`).
6. **Status da #44:** **parcial / bloqueada**. O inventário de código foi produzido; a migração de comportamento, os testes de contrato por comportamento e o ETL de dados não existem.

---

## 2. Contagem e camadas de rotas legadas

### 2.1 Números

| Camada | Quantidade | Evidência |
|---|---:|---|
| Arquivos de rota da SPA | 35 | `LEGACY/src/routes/**` |
| Arquivos com `createServerFn` | 38 (37 de produto + `api/example.functions.ts`) | `LEGACY/src/lib/**` |
| Server functions de produto | **104** | definições `createServerFn` |
| Server functions de demo | 1 (`getGreeting`) | `LEGACY/src/lib/api/example.functions.ts` |
| Métodos das server functions | 15 GET + 89 POST | não há PUT/PATCH/DELETE via server fn |
| Handlers HTTP públicos | **4** em 3 arquivos | `LEGACY/src/routes/api/public/*.ts` |
| Sitemap | 1 GET | `LEGACY/src/routes/sitemap[.]xml.ts` |
| RPCs distintas do Supabase | **106** (89 `v2_*` + 17 globais) | chamadas `rpc("...")` |
| Views expostas | 32 | `LEGACY/src/integrations/supabase/types.ts` |
| Tabelas v2 ativas | ~70 | migrations `0021`, `0022`, `0049`, `0078`, `0079`, `0100`, `0101`, etc. |
| Buckets de storage | 5 | `generated-media`, `video-inputs`, `video-segments`, `video-frames`, `video-final` |
| Migrations legadas | 81 Supabase + 113 Drizzle | `LEGACY/supabase/migrations`, `LEGACY/drizzle/migrations` |

**Caminho físico das server functions:** o código não declara path HTTP literal. `createServerFn` compila para um endpoint interno do TanStack Start, algo como `/_serverFn/<id gerado>`. Para inventário, o “path” confiável é o **nome do handler**. Já as rotas públicas e os RPCs têm paths literais (`/api/public/...` e `/rest/v1/rpc/<nome>`).

### 2.2 Cinco server functions definidas mas sem consumidor de UI

Não encontrei `useServerFn`/import de UI para:

- `generateCampaignBriefing`
- `generateCampaignCopies`
- `generateCampaignPostVariants`
- `fillBrandFromWeb`
- `generateImageWithGemini` (a função interna de mesmo nome em `imagecreator/generator.server.ts` é usada; a server function exportada em `design.functions.ts` não)

Isso reduz o universo “realmente conectado” para ~99 server functions de produto. `generateCampaign*` e `fillBrandFromWeb` devem ser tratados como possível código morto até confirmação de produto.

---

## 3. Inventário de endpoints

### 3.1 HTTP público literal

| Método | Path | Handler | Auth | Request | Response |
|---|---|---|---|---|---|
| GET | `/api/public/hub-metrics` | `LEGACY/src/routes/api/public/hub-metrics.ts` | HMAC-SHA256 de `x-hub-timestamp` com `HUB_METRICS_SECRET`; janela de 5 min | headers `x-hub-timestamp`, `x-hub-signature` | `{ users: [{ email, total, months: {"YYYY-MM": n} }] }` |
| POST | `/api/public/pagarme-webhook` | `LEGACY/src/routes/api/public/pagarme-webhook.ts` | Basic auth com senha `PAGARME_WEBHOOK_SECRET`, `x-webhook-secret` ou `?token=` | payload Pagar.me (`type`, `data`, `status`, `subscription`, `charge`, etc.) | texto `ok` ou `error`; registra `v2_payment_webhook_log` |
| GET, POST | `/api/public/pagarme-reconcile` | `LEGACY/src/routes/api/public/pagarme-reconcile.ts` | `x-webhook-secret`/`?token=` ou token de cron validado por `verify_cron_token('pagarme_reconcile')` | query `hours` (default 168) | `{ checked, updated, results }` |
| GET | `/sitemap.xml` | `LEGACY/src/routes/sitemap[.]xml.ts` | público | — | XML de páginas públicas |

### 3.2 Server functions — autenticação, conta e migração de usuários

Auth: `[público]` ou `[bearer]`; todas as autenticadas usam `requireSupabaseAuth`, que aceita **somente** `Authorization: Bearer <JWT Supabase>`. Respostas são objetos crus; erros são `Error` sem envelope/código.

```text
POST sendSignupConfirmationEmail        [público]  {email,password,redirectTo,metadata?} -> envio Resend
POST sendMagicLinkEmail                 [público]  {email,redirectTo} -> envio Resend
POST sendRecoveryLinkEmail              [público]  {email,redirectTo} -> envio Resend
POST lookupAuthEmail                    [público]  {email} -> {exists,hasPassword,migrated}
POST setInitialPassword                 [público]  {email,password} -> {ok}; só define se a conta ainda NÃO tem senha
POST requestLoginCode                   [público]  {email} -> {sent,expiresInMinutes}
POST verifyLoginCode                    [público]  {email,code} -> {tokenHash} (magiclink gerado via admin)
POST requestPasswordResetCode           [público]  {email} -> {sent,expiresInMinutes}
POST verifyPasswordResetCode            [público]  {email,code} -> {valid:true}
POST resetPasswordWithCode              [público]  {email,code,password} -> {ok}
POST importUsersBatch                   [bearer+admin] {rows:[{user_id,email,name?,phone?,city?,state?,team_id?,team_name?,team_code?,plan_id?,credits?,...}]} -> {created,updated,skipped,errors,teamsCreated,results[]}
POST sendMigrationInvites               [bearer+admin] {emails[],redirectTo} -> {sent,errors[]}
GET  migrationStatus                    [bearer+admin] -> {migratedUsers,withLegacyId,legacyTeams}
GET  listPendingPasswordEmails          [bearer+admin] -> {emails[]}
POST isMigratedAccount                  [público]  {email} -> {migrated:boolean}
```

### 3.3 Server functions — admin

Todas `[bearer+admin]`; `adminAmI` só exige bearer e retorna se é admin. O legado usa `has_role(user,'admin')` ou `requireAdmin`.

```text
GET  adminAmI                          -> {isAdmin}
GET  adminOverview                     -> {users,workspaces,activeCoupons,totalBalance,totalSpent}
GET  adminListUsers                    {search?} -> AdminUser[] (id,email,display_name,avatar_url,created_at,roles[],workspaces)
POST adminSetRole                      {userId,role:"admin"|"gestor"|"membro",enabled} -> {ok}
GET  adminListCoupons                  -> AdminCreditCoupon[]
POST adminSaveCoupon                   {id?,code,credits,max_redemptions,expires_at,note,active} -> {ok}
POST adminDeleteCoupon                 {id} -> {ok}
GET  adminListPlans                    -> AdminPlan[]
POST adminSavePlan                     {id?,name,slug,description,price_brl,monthly_credits,sort_order,active} -> {ok}
POST adminDeletePlan                   {id} -> {ok}
GET  adminListWorkspaces               {search?} -> AdminWorkspace[] (id,name,slug,plan_id,balance,monthly_allowance,purchased_credits,total_spent,members)
POST adminSetWorkspacePlan             {workspaceId,planId|null} -> {ok}
POST adminGrantCredits                 {workspaceId,credits,note?} -> {balance}; positivo = grant/lot, negativo = consume lots
POST adminListOrders                   {status?} -> AdminOrder[]
POST adminListWebhookEvents            {} -> AdminWebhookEvent[]
POST adminSignupReport                 {days?} -> SignupReport (série diária, períodos, últimos cadastros)
POST adminPurchaseReport               {days?} -> PurchaseReport (série, resumo, compradores)
GET  adminListDiscountCoupons          -> AdminDiscountCoupon[]
POST adminSaveDiscountCoupon           {id?,code,percent_off,applies_to,min_amount_cents,max_redemptions,once_per_workspace,expires_at,note,active} -> {ok}
POST adminDeleteDiscountCoupon         {id} -> {ok}
GET  adminListNotificationRecipients   -> AdminNotificationRecipient[]
POST adminSaveNotificationRecipient    {id?,email,label?,notifyCreated?,notifyPaid?,active?} -> {ok}
POST adminDeleteNotificationRecipient  {id} -> {ok}
GET  adminMetrics                      -> métricas de receita/MRR/assinaturas/créditos/gerações/usuários
POST adminUserDetail                   {userId} -> perfil, roles, workspaces, transações, pedidos
POST adminOrderDetail                  {orderId} -> pedido + eventos de webhook
POST adminListCreditTransactions       {search?,limit?,offset?} -> {rows,total}
POST adminListContents                 {limit?,offset?,search?} -> {rows,total}
GET  adminHealth                       -> falhas de webhook/pedido/vídeo, média de vídeo, rejeição
POST adminPurchaseReport               {limit?} -> relatório (versão de admin-insights; duplica nome)
POST adminWorkspaceDetail              {workspaceId} -> workspace, membros, assinatura, créditos, pedidos
POST adminGlobalSearch                 {term} -> {hits:[user|workspace|order]}
GET  adminRedisUsage                   -> uso de chaves Redis por grupo
```

Observação: `adminPurchaseReport` existe em dois módulos (`admin.functions.ts` e `admin-insights.functions.ts`) com shapes diferentes. Isso é dívida de contrato, não equivalência.

### 3.4 Server functions — marca, assets e importação

```text
POST listLinkedBrandAssets      [bearer]       {brandId} -> [{key,label,source:"brand"|"theme"|"persona",dataUrl}]
POST copyBrandFilesToBucket     [bearer+admin] {offset?} -> BrandFilesCopyResult (copia base64 de logo/training para bucket)
POST extractBrandFromText       [bearer]       {text,files:[{name,mimeType,base64}]} -> {extracted,txt}
POST fillBrandFromWeb           [bearer]       {site?,instagram?} -> {extracted,missing}  (sem consumidor de UI)
```

### 3.5 Server functions — criação, copy, design, imagem, mídia e histórico

```text
POST getAiCache                     [bearer] {workspaceId,kind,key} -> {json}
POST setAiCache                     [bearer] {workspaceId,kind,key,body} -> {ok}
POST signAssetUrls                  [bearer] {assetIds[]} -> [{assetId,status,url,thumbnailUrl,width,height}]
POST generateCalendarPosts          [bearer] {brandId?,calendarName,period?,themes[],themeIds?,personaId?,specialDates[],generalNote?,trendNote?,restrictionNote?,referenceCalendar?,counts{estaticos,carrosseis,stories,reels},autoTotal?} -> {estaticos[],carrosseis[],stories[],videos[]}
POST generateCampaignBriefing       [bearer] {prompt,brandId?,format?} -> briefing (sem UI)
POST generateCampaignCopies         [bearer] prompt/campanha -> {variants[]} (sem UI)
POST generateCampaignPostVariants   [bearer] prompt/campanha -> {variants[]} (sem UI)
POST generateCarouselSlide          [bearer] {basePrompt,slideIndex,totalSlides,previousPrompts?,previousImages?,aspect?,contentTitle?,format?,brandId?,legenda?,extra?,tones?,headlineText?,ctaText?,disclaimerText?,adMode?,useBrandAssets?,excludedAssetKeys?,plan?,withText?} -> {slideIndex,prompt,imageDataUrl,plan}
POST generateContentDirections      [bearer] {brandId?,format?,title,goal?,briefing?,currentCopyDirection?,currentCreativeDirection?,note?} -> {copyDirection,creativeDirection}
POST generateCopyWithGemini         [bearer] GenerateCopyInput {view:"legenda"|"design",post,calendar?,brandId?,personaId?,editoriaIds?,direcionamento?,platform?,contentType?,...} -> {text,meta?}
POST runCreation                    [bearer] {runId,request:CreationRequest,image:ImageCreateRequest} -> resultado do pipeline de 4 agentes + estado/artefatos
POST reviewCreation                 [bearer] {runId,imageDataUrl} -> {report:CreativeQAReport|null,correctionLevel}
POST generateDesignPromptFromCopy   [bearer] {title,format,contentTypeLabel,aspect,media,goal?,briefing?,legenda?,direction?,brandId?,themeId?,personaId?,withText?} -> direção criativa + tones
POST generateImageWithGemini        [bearer] GenerateImageInput {description,mode,brandId?,themeId?,personaId?,format?,style?,aspectRatio?,palette?,referenceImages?,useBrandAssets?,...} -> {imageDataUrl,briefingVisual,headline,subtexto,legenda,compliance,audit?} (server fn sem UI)
POST getDraft                       [bearer] {workspaceId,key} -> {json}
POST saveDraft                      [bearer] {workspaceId,key,value} -> {ok}
POST clearDraft                     [bearer] {workspaceId,key} -> {ok}
POST reviewAndPublishFeed           [bearer] {workspaceId,imageUrl,title,comment,kind:"post"|"story"} -> {status:"published"|"rejected"|"error",postId?,review?,message?}
POST loadHistoryPage                [bearer] {workspaceId,offset,type?,brand?,query?,aspect?,ascending?} -> {rows:HistoryPageRow[],total}
POST createImage                    [bearer] ImageCreateRequest -> {imageDataUrl,prompt,model,text?,chargeId?}
POST refineGeneratedImage           [bearer] {imageDataUrl,instruction,aspectRatio?,originalPrompt?,contentTitle?,brandName?,references?,annotatedImageDataUrl?} -> {imageDataUrl,summary?}
POST suggestImageTextFn             [bearer] {brief,contentTitle?,objective?,brandId?,tone?} -> SuggestedImageText
POST indexLearningExample           [bearer] input de exemplo -> resultado de indexação
POST reindexBrandKnowledgeFn        [bearer] {workspaceId,brandId} -> resultado de reindexação
POST backfillLearningIndexFn        [bearer] {workspaceId} -> {indexed}
POST resizeImageToFormat            [bearer] {imageDataUrl,width,height,label?} -> {imageDataUrl}
POST createVideoProject             [bearer] {title,masterPrompt,aspect,visualStyle?,cameraMovement?,lighting?,audio?,dialogue?,notes?,brandId?,themeId?,personaId?,initialImage?,workspaceId?} -> {projectId}
POST prepareVideoScenes             [bearer] {projectId} -> {ok,alreadyPrepared}
POST updateVideoScenePrompt         [bearer] {projectId,sceneNumber,prompt} -> {ok}
POST startVideoScene                [bearer] {projectId,sceneNumber,retry?} -> {status,alreadyRunning}
POST checkVideoScene                [bearer] {projectId,sceneNumber} -> {success,done,status,sceneNumber?}
POST registerVideoSceneFrame        [bearer] {projectId,sceneNumber,frame} -> {ok,path}
POST createFinalVideoUploadUrl      [bearer] {projectId} -> {uploadUrl,token,path,bucket}
POST completeVideoProject           [bearer] {projectId,thumbnail?} -> {ok}
POST cancelVideoProject             [bearer] {projectId} -> {ok}
POST listVideoProjects              [bearer] -> {projects[]}
POST getVideoProject                [bearer] {projectId} -> projeto + cenas
POST deleteVideoProject             [bearer] {projectId} -> {ok}
POST startVideoGeneration           [bearer] StartVideoInput {description,brandId?,themeId?,personaId?,format?,tones?,aspect?,modelId?,durationSeconds?,...} -> {operationName,prompt,compliance}
POST pollVideoGeneration            [bearer] {operationName} -> {status:"pending"|"done",videoUrl}
```

### 3.6 Server functions — billing, créditos e utilitários

```text
GET  getPaymentConfig               [público] -> {publicKey,configured}
POST getBillingOverview             [bearer] {workspaceId} -> {plans,customer,subscription,orders}
POST saveBillingCustomer            [bearer] {workspaceId,name,email,document,phone?} -> {ok}
POST createCheckout                 [bearer] {workspaceId,planId,method:"pix"|"credit_card"|"boleto",cardToken?,recurring?,couponCode?} -> {order:BillingOrder}
POST createCreditPackCheckout       [bearer] {workspaceId,credits,method,cardToken?,couponCode?} -> {order:BillingOrder}
POST getOrderStatus                 [bearer] {orderId} -> {id,status,paid_at,failure_reason} (reconcilia no Pagar.me)
POST cancelSubscription             [bearer] {workspaceId} -> {ok}
POST previewDiscountCoupon          [bearer] {workspaceId?,code,subtotalCents,scope:"subscription"|"credits"} -> {ok,code,percentOff,subtotalCents,discountCents,totalCents} | {ok:false,message}
POST lookupCouponKind               [bearer] {code} -> {kind:"credit"|"discount"|"none",...}
POST sendEmail                      [bearer] {to,subject,html,from?} -> envio Resend
POST sendWorkspaceInviteEmail       [bearer] {token,origin} -> {sent:true}
GET  getSitePricing                 [público] -> {plans[],prices[]} (lê Supabase; fallback vazio)
```

### 3.7 RPCs do Supabase

Path literal: `POST /rest/v1/rpc/<nome>`; autenticação por `apikey` + `Authorization: Bearer <JWT>` (ou anon). Retorno cru em JSON; erros com mensagem textual, sem `request_id`.

**106 nomes distintos** (89 `v2_*` + 17 globais):

```text
auth_email_password_status consume_credit_lots get_workspace_role grant_credit_lot has_role
hub_metrics_by_email is_workspace_member log_ai_cost match_brand_knowledge match_learning_examples
purchase_credits redeem_coupon remove_workspace_members spend_credits spend_credits_once verify_cron_token
workspace_credit_lots v2_accept_workspace_invite v2_activity_attach_asset v2_activity_metadata
v2_admin_count_imported_teams v2_admin_delete_coupon v2_admin_delete_plan v2_admin_save_coupon
v2_admin_save_plan v2_admin_set_role v2_admin_set_workspace_plan v2_billing_order
v2_billing_overview v2_billing_plans v2_brand_bundle v2_brand_training_analyses v2_create_workspace
v2_create_workspace_invite v2_credit_wallet v2_delete_brand v2_delete_campaign v2_delete_invite
v2_delete_persona v2_delete_plan v2_delete_workspace v2_feed_archive v2_feed_comment
v2_feed_comment_like v2_feed_comments v2_feed_list v2_feed_notifications v2_feed_profiles
v2_feed_public_post v2_feed_publish v2_feed_react v2_feed_validate_image v2_get_brand
v2_get_creation_run v2_get_my_profile v2_get_plan v2_get_workspace_invite v2_get_workspace_settings
v2_get_workspace_team v2_history_page v2_images_by_asset v2_import_user_row v2_invite_email_info
v2_leave_workspace v2_legacy_images_by_asset v2_link_image_charge v2_list_brands
v2_list_campaigns v2_list_coupon_redemptions v2_list_credit_transactions v2_list_my_workspaces
v2_list_personas v2_list_plans v2_list_profiles v2_log_activity v2_lookup_user_by_email
v2_migration_status v2_my_roles v2_payment_command v2_payment_email_log v2_payment_webhook_log
v2_record_creation_artifact v2_record_creation_run v2_record_generated_image v2_register_source_image
v2_save_billing_customer v2_save_brand_training_analysis v2_save_workspace_settings
v2_set_invite_active v2_set_member_role v2_slug_available v2_story_delete v2_story_insights
v2_story_like v2_story_list v2_story_publish v2_story_view v2_sync_brand_lists
v2_sync_campaign_hashtags v2_update_design_activity_correction v2_update_my_profile
v2_update_workspace v2_upsert_brands v2_upsert_campaigns v2_upsert_personas v2_upsert_plan
```

Shapes relevantes:

| RPC | Request | Response |
|---|---|---|
| `v2_brand_bundle` | `{_brand_id}` | `{workspace_id, brand:{id,name,color,data}, themes:[{id,title,data}], personas:[{id,name,data}]}` |
| `v2_list_plans` | `{_workspace_id}` | `[{id,name,brand_id,created_at,user_id,brand,qty}]`; `qty` vem de `extra->'qty'` |
| `v2_get_plan` | `{_workspace_id,_id}` | `{id,name,brand_id,created_at,user_id,data}`; `data` é o `extra` JSON |
| `v2_list_posts` | `{_workspace_id,_calendar_id?}` | posts **aprovados** com `legenda` e `design_brief` |
| `v2_history_page` | `{_workspace_id,_offset,_limit,_type?,_brand?,_query?,_aspect?,_ascending?}` | `{rows:[...],total}` com `storageBucket/storageKey` |
| `v2_billing_overview` | `{_workspace_id}` | `{plans,customer,subscription,orders}` |
| `v2_credit_wallet` | `{_workspace_id}` | saldo, allowance, comprados, gastos etc. |
| `spend_credits` / `spend_credits_once` | `{_workspace_id,_action_key,_quantity?,_metadata?,_charge_key?}` | `{charged,balance,monthly_allowance,action_key,label,transaction_id,free?}` |
| `v2_get_creation_run` | `{_id}` | run + `artifacts[]` |
| `v2_feed_list` | `{_workspace_id}` | posts com `hearts`, `shares`, `comments`, `liked_by_me` |

### 3.8 PostgREST, views e acesso direto

- 32 views expostas em `LEGACY/src/integrations/supabase/types.ts`: `credit_extract`, `generated_images_index`, `v_approved_copies`, `v2_admin_*`, `v2_creator_state`, `v2_video_*`, `v2_brand_knowledge`, `v2_learning_examples`, etc.
- O cliente acessa diretamente `v2_video_projects`, `v2_video_scenes`, `v2_generation_feedback`, `v2_learning_examples`, `v2_creator_state`, `v2_brand_knowledge`, `v2_ab_assignments` e os `v2_admin_*`.
- Path implícito: `GET/POST/PATCH/DELETE /rest/v1/<table-ou-view>` com RLS. Isso é uma API CRUD inteira não representada por `createServerFn`.

---

## 4. Comportamentos visíveis ao usuário

### 4.1 Autenticação

- Login progressivo por e-mail: o frontend verifica se a conta existe, se já tem senha e se é migrada (`lookupAuthEmail`).
- Login por senha via Supabase; login por código de 6 dígitos (`requestLoginCode`/`verifyLoginCode`), magic link, recuperação por link e por código.
- Google OAuth via integração Lovable (`LEGACY/src/routes/auth.tsx` e `src/integrations/lovable`).
- Cadastro com confirmação de e-mail via Resend; contas migradas recebem convite e definem a senha inicial.
- Admin pode importar usuários em lote e disparar convites de migração.
- Rotas: `/auth`, `/auth/callback`, `/reset-password`, `/invite/$token`, `/checkout`.

### 4.2 Workspace e equipe

- Múltiplos workspaces por usuário, troca de workspace ativo no header.
- Dono/admin/editor/viewer; convites por e-mail ou link; aceite; reenvio; revogação; remoção de membros; sair do workspace; apagar workspace.
- Slug do workspace, nome, e configurações por funcionalidade: `allow_calendar`, `allow_campaign`, `allow_copy`, `allow_design`, `allow_video`, `allow_brand`, `allow_persona`, limites mensais e `max_posts_per_calendar`.
- `workspace_settings` é uma tabela central e o frontend a usa para esconder/limitar funcionalidades.

### 4.3 Marca, temas e personas

- Marca com nome, segmento, promessa, valores, keywords, objetivos, indicadores, inspirações, restrições, datas especiais, referências de conteúdo, marcos, colaborações, crises, responsável, linguagem visual, estilos a evitar, logo, variações de logo, referência, moodboard, imagens de treino, paleta e links.
- Importação de marca por texto, arquivos (PDF/imagem) e, no código, por site/Instagram (sem consumidor de UI no momento).
- Temas/editorias com título, descrição, tom de voz, público, objetivos, macroeditorias, ação esperada, hashtags, formatos, plataformas e informações adicionais.
- Personas com nome, categoria, descrição, idade, cidade, foto e detalhes: gênero, contexto profissional, objetivo, desafios, crenças, rotina de conteúdo, tom, estágio de compra e gatilhos.
- Treinamento visual da marca, análise de imagens e RAG (`brand_knowledge`, `learning_examples`, `ab_assignments`).

**Atenção semântica:** a tabela `v2.campaigns` do legado representa **temas/editorias**, não “campanhas” no sentido atual do Creator. O `CampaignPanel.tsx` legado é a tela de **desdobramento/redimensionamento**, não a entidade campanha.

### 4.4 Fluxo calendário → copy → design → desdobramento

1. **Calendário** (`CalendarPanel.tsx`): escolhe marca, período, temas, persona, datas especiais, notas, referência e quantidades por formato (estáticos, carrosséis, stories, reels). Gera os posts com IA (`generateCalendarPosts`) e salva o planejamento.
2. **Copy** (`CopyPanel.tsx`): por post, gera legenda e/ou design brief, direções de copy e criativa, variantes, aprova/rejeita, salva cópia aprovada, registra feedback de aprendizado e desconta créditos.
3. **Design** (`DesignPanel.tsx`): gera imagem via pipeline de 4 agentes (`AGT01` estratégia, `AGT02` direção, `AGT03` visual, `AGT04` crítica) ou via `createImage`; permite refinar com markup, aplicar texto/overlay, gerar carrossel, redimensionar/desdobrar, gerar vídeo e publicar no feed.
4. **Desdobramento** (`CampaignPanel.tsx`): redimensiona uma imagem para 20+ presets (Instagram, Facebook, LinkedIn, X, Pinterest, WhatsApp, anúncios, impressos).
5. **Resultado** (`app.resultado.tsx`): abre a mídia gerada, versões e correções.

### 4.5 Histórico, feed e vídeo

- **Histórico** (`HistoryView.tsx`, `v2_history_page`): lista imagens/vídeos/publicações com filtros por tipo, marca, busca, aspect ratio, ordenação, grade/lista, abertura do resultado e assinatura de URLs.
- **Feed** (`FeedView.tsx`, `publishedFeed.ts`): posts da comunidade, comentários, respostas, likes, shares, menções, stories, visualizações, insights, notificações e revisão pré-publicação por IA.
- **Vídeo 30s** (`VideoStudioView.tsx`, `video30.*`): projeto com 4 cenas de 8s, prompts por cena, frames, upload final, thumbnail, custo estimado, cancelamento e listagem.
- **Vídeo avulso** (`video.functions.ts`): geração Veo, polling por `operationName`, compliance e URL assinada.

### 4.6 Créditos e billing

- Carteira com saldo, allowance mensal, créditos comprados, total gasto e lotes com expiração.
- Consumo por ação: `brand.create`, `persona.create`, `theme.create`, `calendar.posts`, `content.directions`, `design.brief_ai`, `design.image`, `design.image_refine`, `design.carousel_slide`, `design.resize`, `video.script_30s`, `video.scene_30s`.
- Franquias grátis: 3 marcas, 3 temas e 3 personas por workspace; 2 correções grátis por imagem; admin não paga essas ações.
- Limites mensais por feature e bloqueio por `MONTHLY_LIMIT_REACHED`/`FEATURE_DISABLED`.
- Planos com preço, créditos mensais, intervalo, trial; checkout com Pix, cartão e boleto; assinatura recorrente; cupons de desconto e de crédito; pedidos, faturas, cobranças, reembolsos, disputas e webhooks Pagar.me.
- Reconciliação de pedidos pendentes por cron e por polling do checkout.

### 4.7 Admin

- Dashboard de receita/MRR/assinaturas/créditos/gerações/usuários.
- Usuários, roles globais, workspaces, planos, cupons de crédito/desconto, destinatários de e-mail de compra.
- Pedidos, eventos de webhook, relatórios de cadastro/compra, saúde (webhooks/pedidos/vídeos/feedback), uso de Redis e busca global.
- Importação de usuários e status da migração.

---

## 5. Modelo de dados legado

O schema canônico é **`v2`**; muitas tabelas `public` foram dropadas ou viraram views/arquivos de backup. As migrations finais estão em `LEGACY/drizzle/migrations/0021` a `0111`.

| Domínio | Tabelas principais | Relações / observações |
|---|---|---|
| Identidade | `users`, `workspaces`, `workspace_members`, `workspace_invites`, `workspace_invite_usages`, `user_roles`, `workspace_settings`, `creator_state` | workspace 1:N membros/convites/settings/state; `creator_state` unique `(workspace_id,user_id,key)`; roles em tabela separada |
| Marca | `brands`, `brand_values`, `brand_hashtags`, `brand_colors`, `brand_assets`, `brand_business_details`, `brand_documents`, `brand_knowledge`, `brand_training_analyses`, `learning_examples` | brand 1:N listas/assets/temas/personas/planos/conhecimento; `brand_business_details` liga brand+campaign+persona |
| Estratégia | `campaigns` (temas), `campaign_hashtags`, `campaign_voices`, `personas`, `persona_interests`, `content_plans`, `content_plan_items`, `content_plan_special_dates` | campaign/persona brand-scoped; content_plan liga brand/campaign/persona e 1:N items/datas/posts |
| Conteúdo | `posts`, `captions`, `post_designs`, `design_slides`, `generated_images`, `image_resizes`, `video_designs`, `video_scenes`, `generated_videos` | post 1:N captions/designs; design 1:N slides; slide 1:N imagens; video_design 1:N cenas/vídeos |
| Criação/feedback | `creation_runs`, `creation_artifacts`, `generation_feedback`, `ab_assignments` | run 1:N artifacts; feedback/AB por workspace/brand |
| Vídeo | `video_projects`, `video_render_scenes`, `video_generation_attempts` | project 1:N cenas/tentativas; buckets `video-*` |
| Créditos | `workspace_credit_transactions`, `workspace_credit_lots`, `workspace_credit_lot_consumptions`, `credit_charge_keys`, `credit_transaction_details`, `ai_cost_rules`, `free_allowance_uses` | ledger por workspace; lot 1:N consumptions; transaction 1:N details |
| Billing | `billing_accounts`, `billing_addresses`, `billing_payment_methods`, `plans`, `plan_items`, `plan_payment_methods`, `subscriptions`, `subscription_history`, `orders`, `invoices`, `charges`, `charge_transactions`, `refunds`, `provider_disputes`, `provider_webhook_events`, `provider_idempotency_keys`, `credit_packages`, `coupons`, `coupon_redemptions`, `audit_logs`, `fiscal_invoices` | account 1:N endereços/métodos/assinaturas/pedidos/faturas/cobranças/reembolsos; plano 1:N itens/métodos/assinaturas |
| Feed/atividade | `feed_posts`, `feed_post_comments`, `feed_post_reactions`, `feed_stories`, `feed_story_likes`, `feed_story_views`, `feed_publication_reviews`, `activity_log` | posts 1:N comentários/reações; stories separados; activity por workspace |
| Notificações/admin | `notifications`, `purchase_email_recipients`, `user_roles`, `audit_logs`, `fiscal_invoices` | várias tabelas de notificação/preferências foram dropadas em `0095` |
| Storage | `generated-media`, `video-inputs`, `video-segments`, `video-frames`, `video-final` | referências por `storage_bucket/storage_key` |

### 5.1 O dado “real” está em JSON, não nas colunas tipadas

Isso é central para qualquer ETL:

- `v2.brands.extra` contém nome, cor, segmento, promessa, valores, keywords, goals, indicadores, inspirações, datas especiais, referências, restrições, marcos, colaborações, crises, responsável, linguagem visual, estilos a evitar, logo, variações, referência, moodboard, imagens de treino e paleta. `v2_brand_bundle` devolve `extra` como `data`.
- `v2.campaigns.extra` contém os campos editoriais reais (título, descrição, voiceTones, voiceTone, audience, goals, macroEditorias, expectedAction, hashtags, contentFormat, bestFormats, platforms, additionalInfo).
- `v2.personas.extra` contém categoria, descrição, idade, cidade, foto e `details` (gênero, contexto profissional, objetivo, desafios, crenças, rotina, tom, estágio de compra, gatilhos).
- `v2.content_plans.extra` contém `brand`, `persona`, `personaId`, `qty`, `counts`, `themes`, `themeIds`, `specialDates`, `generalNote`, `trendNote`, `restrictionNote`, `referenceCalendar`, `period`, `createdAt`, status legado. As colunas tipadas são derivadas e incompletas.
- `v2.creator_state.value` guarda, por workspace+usuário+chave: `calendar:draft`, `copy:state`, `copy:drafts`, `copy:posts:<calendarId>`, `copy:requestedCals`, `design:gallery:<calendarId>`, `design:versions:<...>`, `design:last:*`, `settings:notifications`, progresso de tutorial, fontes customizadas, etc.
- `v2.posts` só contém posts **aprovados** (`v2_list_posts` filtra `approval_status='APPROVED'`). Posts planejados não aprovados existem apenas no JSON `copy:posts:<calendarId>`.

### 5.2 Tabelas dropadas/arquivadas

- `0092_content_v2_only.sql` dropa `public.brands`, `public.personas`, `public.editorias`, `public.calendars`.
- `0093_activity_invites_settings_v2_only.sql` dropa `public.activity_log`, `public.workspace_invites`, `public.workspace_settings`.
- `0094_drop_last_legacy_table.sql` dropa `public.cron_secrets`.
- `0095_drop_unused_empty_v2_tables.sql` dropa `notification_recipients`, `notification_preferences`, `user_devices`, `persona_interests`, `user_consents`, `subscription_history`, `provider_idempotency_keys`, `workspace_invite_usages`, `video_scenes`.
- Tabelas `v2.legacy_*` são backups, não fonte canônica. Não migrar em dobro.

---

## 6. Backend atual — o que existe

### 6.1 Números

| Item | Valor |
|---|---|
| Routers de capacidade | 27 |
| Paths OpenAPI | **103** |
| Operações OpenAPI | **227** |
| Tabelas ORM | **51** |
| Migrations Alembic | 6 (`0001` a `0004`, com duas `0003`) |
| Auth | login, signup, refresh, csrf, logout (cookies HttpOnly; sem Bearer) |
| Envelope | `{ success, data, meta.request_id }` + `X-Request-ID` |
| Geração assíncrona | `GenerationJob` + RQ/Redis; `Idempotency-Key` em imagens |
| Workflow | `AgentWorkflowRun`/`Step`, roles BUSINESS/PLANNER/WRITER/ARTIST/REVIEWER/DELIVERY |
| RAG | interfaces existem, fábrica sempre retorna provider “unconfigured” |
| Pagamentos | CRUD de billing; nenhum adapter Pagar.me, webhook ou checkout |
| Créditos | CRUD de `workspace_credit_transactions`; sem wallet/lots/consumo |

### 6.2 Recursos e cobertura atual

- **Auth:** `/api/v1/auth/login`, `/signup`, `/refresh`, `/csrf`, `/logout`. Sem recuperação de senha, confirmação de e-mail, OTP, magic link, OAuth ou importação.
- **Usuários/perfil:** `/users/me`, `/settings` (settings de geração do usuário), `/users` CRUD admin. Sem phone/city/state; sem metadata de migração.
- **Workspace:** `/workspaces` CRUD (apenas `name`), `/workspace-invites` CRUD, `/workspace-invite-usages` CRUD. Sem slug, owner, plano, feature flags, limites, aceite de convite, alteração de role, remoção/leave.
- **Marca:** `/brands` CRUD, `/brands/{id}/settings`, `/brand-assets` CRUD, `/brand-colors` CRUD. Sem upload, importação, knowledge, training, listas de valores/hashtags.
- **Campanha/persona/planning:** `/campaigns`, `/personas`, `/planning` CRUD. `Campaign` é workspace-scoped, sem brand_id/metadata; `Planning` exige campaign/persona e não tem nome/metadata; `Persona` tem 9 campos e limites curtos.
- **Post/design:** `/post-structures`, `/design-structures` CRUD. `post_structure` não tem briefing/design brief/captions/aprovação; `design_structure` só tem `post_structure_id`.
- **Projetos:** `/projects` CRUD (novo, sem equivalente legado; `docs/SCHEMA-MIGRATION-MATRIX.md` o trata como transitório).
- **Content:** `/contents` CRUD, `/content/{id}`, `/content` list, `/content/generate`, `/content/improve`. Geração de texto é genérica (`topic`, `audience`, `tone`, `content_type`, `brand_voice`), não o fluxo de copy por post.
- **Geração/imagem:** `/generations` CRUD, `/images/generate`, `/images/{id}`, `/images/{id}/regenerate`, `/generated-images/{id}`, `/generations/image-workflows`, `/steps`, `/decision`. Imagem é Gemini com prompt genérico + `style`; workflow tem Business→Planner→Writer→Artist→Reviewer, mas não composição de marca, overlay, carrossel, resize ou vídeo.
- **Assets:** `/assets` CRUD apenas de metadados (`storage_path`, `public_url`, `byte_size`, etc.); não há endpoint de upload nem de assinatura em lote.
- **Billing:** CRUD de `subscription-history`, `billing-addresses`, `billing-payment-methods`, `billing-accounts`, `subscriptions`, `invoices`, `charges`, `orders`, `coupon-redemptions`, `provider-customers`, `provider-subscriptions`, `provider-webhook-events`, `provider-idempotency-keys`, `refunds`, `provider-disputes`, `coupons`, `credit-packages`, `plans`, `plan-items`. Sem provider real, checkout, webhook ou reconciliação.
- **Créditos:** `/workspace-credit-transactions` CRUD. Sem wallet, saldo, lotes, expiração, consumo, free allowance ou preço por ação.
- **Notificações:** `/notifications`, `/notification-recipients`, `/user-devices`, `/notification-preferences` CRUD. Sem envio de e-mail/push nem entrega.
- **Sistema:** `/health`, `/health/live`, `/metrics` — novos, não existem no legado.

### 6.3 Lacunas de schema atuais que impedem o mapeamento direto

| Modelo atual | O que falta em relação ao legado |
|---|---|
| `plans` | `price_cents`, `credits_per_month`, `currency`, `billing_interval`, `interval_count`, `trial_period_days`, `external_id` etc.; hoje só `code/type/name/description/metadata/is_active` |
| `orders` | `plan_name`, `credits`, `payment_method`, `pix_qr_code`, `boleto_*`, `provider_order_id` com semântica Pagar.me; hoje faltam colunas de checkout |
| `subscriptions` | `contracted_price_cents`, `currency`, `current_cycle_id`, `payment_method_id`, `status_reason` etc. |
| `workspace_credit_transactions` | `balance_after`, `type` com semântica de ledger, `order_id/invoice_id/generated_image_id/...`, lotes e consumos |
| `workspaces` | `slug`, `owner_id`, `plan_id`, `legacy_team_id`, `legacy_team_code`, `metadata` |
| `campaigns` | `brand_id`, `metadata`/`extra`, hashtags, voices, expected_action |
| `personas` | `metadata`/`extra`, interests, categoria, cidade, foto, detalhes |
| `planning` | `name`, `metadata`/`extra`, items por formato, datas especiais estruturadas |
| `post_structure` | `briefing`, `design_brief`, `captions`, approval/publication status, scheduling |
| `design_structure` | praticamente todos os atributos de design/slides |
| `generated_image` | `storage_bucket/key`, `mime_type`, `size`, `width/height`, `model`, `prompt`, `approval_status`; a tabela atual só tem `signed_url/size/resolution/image_ratio/image_status` e **não encontrei write path** para ela |
| `users` | phone/city/state, metadata de migração, roles múltiplas; hoje só `display_name/bio/cpf/cnpj/avatar/global_role` |

---

## 7. Matriz de equivalência resumida

Status: **Equivalente** = contrato + dados + comportamento; **Parcial** = existe endpoint/modelo, mas falta comportamento/campo relevante; **Ausente** = não há equivalente; **Novo/Fora** = não é paridade legada.

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

## 8. Top 10 lacunas que impedem a conclusão

1. **Autenticação incompleta.** `CURRENT/src/creator/auth/router.py` tem só login/signup/refresh/csrf/logout; o legado tem 15 funções de conta (OTP, magic link, reset, confirmação, OAuth, importação, convite de senha). Hashes Supabase não migram para Argon2.
2. **Billing/Pagar.me inexistente.** `CURRENT/src/creator/billing_provider/router.py` é CRUD; não há `pagarme.server.ts`, checkout, webhook, reconcile, cancelamento real, faturas ou cobranças. `plans`/`orders`/`subscriptions` atuais não têm colunas para os dados legados.
3. **Créditos não funcionam como ledger.** `CURRENT/src/creator/credit/service.py` é CRUD; não há wallet, `balance_after`, lotes, expiração, consumo por geração, free allowances ou `ai_cost_rules`. `generation/service.py` não debita créditos.
4. **Pipeline calendário→copy→design ausente.** O atual só tem `/content/generate` e `/content/improve` genéricos; não há geração de calendário, copy por post, direções, design brief, carrossel, resize/desdobramento.
5. **Fidelidade da geração de imagem.** O atual usa prompt genérico + `style`; não há composição com brand assets, referências, palette/text lock, overlay, auditoria multimodal, versões e aprovação. `generated_image` atual é uma tabela esparsa sem writer; `images` é o destino real.
6. **Vídeo ausente.** Não há modelos nem endpoints para projetos de 30s, cenas, frames, polling Veo ou vídeo avulso.
7. **Feed/comunidade ausente.** Não há posts, comentários, likes, respostas, stories, notificações ou revisão pré-publicação.
8. **Workspace/equipe incompletos.** Sem slug, owner, plano, feature flags, limites mensais, aceite de convite, alteração de role, remoção de membro, leave ou team payload.
9. **Fidelidade de marca/tema/persona/planning.** `Campaign`, `Persona`, `Planning`, `PostStructure` e `Workspace` não têm `metadata`/`extra`; os limites atuais truncam textos legados; não há `brand_values`, `brand_hashtags`, `persona_interests`, `brand_knowledge`, `learning_examples`, `ab_assignments`.
10. **Admin, histórico, uploads, e-mail e APIs públicas.** Não há admin de métricas/relatórios/catálogo, activity/history, upload/signed URLs, envio de e-mail ou rotas públicas de webhook/hub metrics.

Além dessas 10, há um bloqueio transversal: **não existe teste de contrato por comportamento legado** nem **ETL executável**. Os testes atuais (`CURRENT/tests/**`) validam apenas o contrato atual; `tests/contracts/route_table.json` tem 227 operações atuais e nenhum vínculo com o legado.

---

## 9. Riscos de dados/ETL

### P0 — bloqueiam qualquer migração segura

1. **Não há snapshot de dados.** O clone é somente código; não localizei dump, contagens de linhas, amostras ou export do storage. Não é possível validar FKs, órfãos, duplicatas ou volume.
2. **Senhas não são migráveis.** O legado usa Supabase Auth (schema `auth.users`, fora das tabelas da aplicação). O atual usa Argon2 local. É obrigatório forçar reset/definir senha; não copiar hashes.
3. **`creator_state` e `extra` são a fonte real.** Grande parte do calendário, posts não aprovados, galeria, versões, rascunhos e preferências vive em JSON por workspace+usuário. O atual não tem tabela equivalente e `Campaign/Persona/Planning/PostStructure/Workspace` não têm `metadata`.
4. **Dados podem existir só no navegador.** `remoteStore.ts` limita a escrita remota a 300 KB (`MAX_REMOTE_BYTES`) e marca valores grandes como `localOnly`; não há como recuperar esses dados do banco.
5. **Billing/créditos não cabem no schema atual.** `plans` sem preço/créditos, `orders` sem plano/créditos/método/Pix/boleto, `subscriptions` sem preço contratado/ciclo, `workspace_credit_transactions` sem `balance_after`/lotes. Migrar agora perde ou corrompe dados financeiros.
6. **Storage heterogêneo.** `generated-media` (imagens, brand-files, community-reviewed), `video-inputs/segments/frames/final`, URLs assinadas de 1 ano, referências `external-url` e host morto `afxwqkrneraatgovhpkb.supabase.co`. O atual só suporta imagens e não tem upload público.

### P1 — exigem transformação e validação

7. **IDs textuais vs UUIDs.** O legado usa `legacy_ref`/`legacy_id` textuais e IDs de UI em JSON; o atual usa FKs UUID. Sem tabela de mapeamento determinístico, links de calendário/post/imagem/brand quebram.
8. **Truncamento de campos.** Exemplos: `campaigns.name` 30 vs 150; `personas.name` 30 vs 150, `main_goal` 60 vs 1000, `challenge` 50 vs 1000; `planning.info` 400 vs 4000; `post_structure.title` 100 vs 250, `objective` 300 vs 1500, `big_idea`/`main_message` 150 vs 1000. Sem extensão ou JSON, o ETL trunca.
9. **Enums/status/papéis.** `workspace_role` legado é owner/admin/editor/viewer; `user_roles` é many-to-many e o atual tem um único `global_role`. Status de assinatura, pedido, cobrança, aprovação e publicação também diferem. Precisa de tabela de mapeamento explícita.
10. **Registros duplicados/órfãos.** `v2.legacy_*`, `public` views, `generated_images` + `legacy_generation_outputs`, `video_scenes` vs `video_render_scenes`, múltiplas assinaturas ativas e cupons duplicados. O atual tem índices únicos parciais que podem falhar no load.
11. **Tabelas dropadas não têm fonte.** `notification_recipients`, `notification_preferences`, `user_devices`, `subscription_history`, `provider_idempotency_keys`, `workspace_invite_usages`, `persona_interests`, `user_consents` foram dropadas em `0095`; o atual deve começar vazio ou derivar de outra fonte.
12. **PII/LGPD.** CPF no legado é `bytea` + hash; no atual é string; `document` de billing é string; tokens de convite são plaintext/hash; `user_consents` não existe no atual. Precisa de política de retenção, hash/criptografia e revisão jurídica.
13. **Portabilidade SQLite.** `jsonb`, `vector(3072)`, `bytea`, arrays e enums nativos não são portáveis. O atual usa tipos portáveis; o ETL precisa converter e testar em SQLite e Postgres.
14. **Dados de marca em base64.** Logos, moodboards e `trainingImages` podem estar inline no JSON; `brand-files-copy` existe justamente para extrair. O ETL deve separar arquivo de metadado e evitar inflar `metadata`/SQLite.

---

## 10. Recomendação de status da #44

### Critérios de aceite atuais

| Critério | Evidência | Status |
|---|---|---|
| Snapshot/accesso ao legado disponível | clone `1dd4b41`, branch `main` | **Parcial**: código sim; dados/storage não |
| Rotas, shapes e comportamentos inventariados | este relatório | **Atendido no código**; parcial nos dados |
| Cada comportamento migrado tem contract test e link para a issue | nenhum teste legado→atual | **Não atendido** |

### Recomendação

**Não concluir a #44.** Status recomendado: **parcialmente atendida / bloqueada para migração**. Se for necessário um status binário, use **bloqueada**, não “concluída”.

Justificativa:

- O inventário de código agora existe, mas não há dump de dados nem reconciliation.
- Não há contract tests por comportamento; os 227 testes/rotas atuais não referenciam o legado.
- Faltam capacidades visíveis inteiras: auth completo, billing provider, créditos, planejamento/copy/design, vídeo, feed, admin.
- O próprio backend atual é transitório: `CURRENT/docs/SCHEMA-MIGRATION-MATRIX.md` ainda planeja trocar `Content`→`post_structure`, `Generation`→`design_structure`, `Image`→`generated_image`, `Project`→`campaigns/planning`. Migrar o legado para tabelas que ainda serão substituídas criaria uma segunda migração.
- O frontend atual ainda usa Bearer; o backend atual só aceita cookies. O cutover do SPA (`CURRENT/docs/spa-cookie-auth-migration.md`, issue #128) está pendente de sign-off.

### Condições para desbloquear

1. Congelar o snapshot legado (commit + dump read-only do schema `v2` + storage) com contagens e política de PII.
2. Aprovar uma matriz de escopo explícita: feed, vídeo, admin, RAG, OAuth e billing podem ser “fora de escopo” somente via ADR/decisão de produto.
3. Decidir a estratégia de auth: reset obrigatório de senha, preservação ou não de UUIDs, campanha de convite e cutover Supabase→local.
4. Antes do ETL, adicionar ao alvo `metadata`/`legacy_ref` em `Workspace`, `Campaign`, `Persona`, `Planning`, `PostStructure` e `DesignStructure` — ou criar uma camada de arquivo legado read-only.
5. Separar a migração em sub-issues: auth, workspace/team, brand/strategy, planning/content, image/agent, video, feed, billing/credits, admin, ETL.
6. Para cada comportamento, escrever contract test que reproduza o fluxo legado e linkar à #44 antes de fechar a sub-issue.
7. Fazer dry-run de ETL com reconciliação de IDs, saldos, assinaturas, storage e contagens.
8. Só então reavaliar se #44 pode ser fechada; hoje ela deve permanecer aberta e marcada como bloqueada.

---

## 11. Evidências principais

### Legado

- `LEGACY/src/lib/*.functions.ts` — 37 arquivos, 104 server functions de produto.
- `LEGACY/src/routes/api/public/hub-metrics.ts`, `pagarme-webhook.ts`, `pagarme-reconcile.ts` — 4 handlers públicos.
- `LEGACY/src/integrations/supabase/auth-middleware.ts` — Bearer-only, Supabase JWT.
- `LEGACY/src/lib/identityV2.ts` — perfil/workspace/team/invites via RPC.
- `LEGACY/src/lib/payments.functions.ts` — checkout, billing overview, cupons, assinatura.
- `LEGACY/src/lib/credits.ts` — wallet, spend, lots, coupons.
- `LEGACY/src/lib/video30.functions.ts`, `video.functions.ts` — vídeo.
- `LEGACY/src/components/creators/CalendarPanel.tsx`, `CopyPanel.tsx`, `DesignPanel.tsx`, `CampaignPanel.tsx` — fluxo principal.
- `LEGACY/src/components/BrandsView.tsx`, `ThemesView.tsx`, `PersonasView.tsx` — catálogo.
- `LEGACY/src/components/HistoryView.tsx`, `FeedView.tsx`, `VideoStudioView.tsx` — histórico/feed/vídeo.
- `LEGACY/drizzle/migrations/0021_v2_part1_enums_billing.sql`, `0022_v2_part2_content_tables.sql` — schema core.
- `LEGACY/drizzle/migrations/0036_v2_posts_history_rpcs.sql` — posts aprovados/histórico.
- `LEGACY/drizzle/migrations/0049_v2_feed_activity_video_settings.sql` — feed/activity/settings.
- `LEGACY/drizzle/migrations/0078_v2_video_feedback_knowledge.sql`, `0079_v2_creator_state.sql` — knowledge/creator_state.
- `LEGACY/drizzle/migrations/0090_identity_v2_only.sql` a `0095_drop_unused_empty_v2_tables.sql` — corte para v2/drops.
- `LEGACY/drizzle/migrations/0100_free_allowances.sql`, `0101_creation_agents.sql`, `0104`, `0105`–`0111` — créditos, criação, feed/stories.
- `LEGACY/src/integrations/supabase/types.ts` — 32 views e assinaturas de RPC.

### Atual

- `CURRENT/src/creator/auth/router.py` — 5 rotas de auth.
- `CURRENT/src/creator/workspace/models.py` — workspace sem slug/owner/settings.
- `CURRENT/src/creator/brand/models.py` — brand/settings/colors/assets.
- `CURRENT/src/creator/campaign/models.py`, `persona/models.py`, `planning/models.py`, `post_structure/models.py`, `design_structure/models.py` — modelo simplificado.
- `CURRENT/src/creator/content/models.py`, `generation/models.py` — content/images/generations/jobs.
- `CURRENT/src/creator/plan/models.py`, `order/models.py`, `subscription/models.py`, `credit/models.py` — billing/créditos incompletos.
- `CURRENT/src/creator/billing_provider/router.py`, `credit/service.py`, `content/router.py`, `generation/router.py`, `workflow/router.py` — CRUD/geração atuais.
- `CURRENT/src/creator/services/retrieval/factory.py` — RAG sempre “unconfigured”.
- `CURRENT/docs/openapi.yaml` — 103 paths/227 operações.
- `CURRENT/tests/contracts/route_table.json` — 227 operações atuais.
- `CURRENT/docs/SCHEMA-MIGRATION-MATRIX.md` — dívida de schema ainda aberta.
- `CURRENT/docs/status-do-projeto.md` — Brand Knowledge/#49, créditos/#54, COPY/CAPTION/#79 e RAG/#73–#77 pendentes.
- `CURRENT/docs/issues/0011-source-migration-inventory.md` — critérios de aceite da #44.
- `CURRENT/docs/spa-cookie-auth-migration.md` — cutover de cookie ainda depende de sign-off do frontend.
</subagent>