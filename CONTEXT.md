# Creator

Creator is a multi-tenant platform for planning, generating, reviewing, and managing marketing content with AI assistance. It is built for marketing agencies and in-house content teams; a Workspace is the tenant boundary for one operation.

## Product intent

Creator turns a brand briefing into content ready for review and publication with brand context, governance, and scale. It reduces operational work — resizing, adapting, rewriting, searching for briefs, organizing references, and starting every piece from zero — while keeping the creative concept human-owned. AI amplifies a good concept; it does not replace it.

The product is measured by time saved, quality and reduced rework, the capacity to explore variations from one approved idea, and creative leverage. Raw output volume is not the primary success metric.

## Core flow

Brand Context → Briefing → Campaign → Planning (editorial calendar) → Post Structure → Generation or Agent Workflow → Content draft → Automated Review → Human Review → Approval → Publication → Performance Signal → Content Feedback → next Generation.

Not every step is implemented in the current backend. The flow defines the business vocabulary and the direction of the product; `docs/status-do-projeto.md` records implementation status.

## Language

**Creator**:
The application as a whole. It contains several business capabilities and is not the name of an individual workflow or generated artifact.
_Avoid_: Create Bloom, Creator Bloom

**Workspace**:
The tenant boundary that owns business data, memberships, permissions, usage, credits, billing, and generated artifacts.
_Avoid_: Account, organization, team

**Global Role**:
A person's platform-wide authority, independent of any individual Workspace. The canonical values are `admin`, `gestor`, and `membro`.
_Avoid_: System permission, workspace role

**Workspace Role**:
A membership's authority inside one Workspace. The canonical values are `owner`, `admin`, `editor`, and `viewer`.
_Avoid_: Global role, user type

**Principal**:
The authenticated identity derived from a valid Creator access token. A Principal proves who is making a request but does not by itself prove access to a Workspace.
_Avoid_: User record, membership, session

**Auth Session**:
A revocable login relationship represented by one rotating refresh-token family. It may issue multiple short-lived access tokens over its lifetime.
_Avoid_: Access token, JWT, user

**Brand**:
The marketing identity owned by a Workspace. It scopes Brand Context, Brand Knowledge, Personas, and brand-aligned Generations.
_Avoid_: Client, company, account

**Brand Context**:
The Workspace- and Brand-scoped set of signals that grounds Generations: positioning, values, voice, visual identity, palette, personas, strategic themes, references, and restrictions. Brand Context is assembled from Brand Settings, the brand color palette, Brand Assets, Personas, and Brand Knowledge; it is not a separate tenant boundary.
_Avoid_: Brand DNA, brand memory, RAG data

**Brand Settings**:
The Brand-scoped configuration of voice, visual, and generation defaults. Brand Settings is part of Brand Context, not a separate tenant boundary.
_Avoid_: Preferences, config

**Brand Knowledge**:
Workspace- and Brand-scoped source material used as retrieval context for Generations and agent workflows.
_Avoid_: RAG data, vector store, document

**Briefing**:
The structured creative input for a Campaign or Post: objective, audience, key message, references, constraints, and desired formats. A Briefing is input to a Generation or Agent Workflow; it is not Content. The current backend carries briefing data inside the workflow input and the Writer's design direction; a first-class persisted Briefing is not yet implemented.
_Avoid_: Prompt, request (when referring to business input)

**Creative Concept**:
The human-authored idea or angle that a Generation must preserve and develop. It precedes copy and design and constrains both; it is not generated Content.
_Avoid_: Big idea (reserved for the Post Structure field), prompt

**Content**:
A persisted marketing artifact produced or managed by Creator, such as copy or an image. It is the output of a workflow, not the workflow itself.
_Avoid_: Creator, generation, job

**Content Type**:
The persisted representation of Content: `IMAGE` or `TEXT`. It is distinct from Artifact Type, which describes what a Generation Job produces.
_Avoid_: Artifact type, media type

**Content Format**:
The publishing shape of a Post Structure or Content: `STATIC`, `CAROUSEL`, or `STORIES`. It is distinct from Artifact Type and Content Type.
_Avoid_: Post type, media type

**Content Version**:
An immutable revision of Content or of a generated artifact. Regeneration creates a new version; it does not overwrite the prior version.
_Avoid_: Copy, duplicate, image (when referring to a revision)

**Variation**:
A derived artifact that preserves the source Content's concept and Brand Context while changing copy, format, ratio, or visual treatment. A Variation is produced by a `TRANSFORM` or `REGENERATE` Generation and should be persisted as a new Content Version when the owning capability supports versions.
_Avoid_: Version (when referring to creative intent), copy

**Generation**:
A request to an AI provider to produce or transform Content for a Workspace. A Generation may complete synchronously; when execution is asynchronous, a Generation Job performs it.
_Avoid_: Content, job, task

**Generation Job**:
The durable asynchronous execution of a Generation, including its lifecycle, attempts, result, and failure information.
_Avoid_: Generation, request, queue message

**Artifact Type**:
The kind of output a Generation Job produces: `IMAGE`, `COPY`, or `CAPTION`. Design composition and carousel layout are not Artifact Types; they are Content Format and Post Structure concerns.
_Avoid_: Content type, media type

**Generation Operation**:
The intent of a Generation Job: `CREATE`, `REGENERATE`, or `TRANSFORM`.
_Avoid_: Action, mode

**Agent Workflow**:
A durable multi-step Generation executed by specialist roles and persisted as runs and steps. Creator owns its state transitions; CrewAI is an adapter, not the workflow engine.
_Avoid_: Crew, pipeline, job

**Specialist Role**:
One of the roles in an Agent Workflow: Business, Planner, Writer, Artist, and Reviewer. Artist and Reviewer are provider-backed capabilities; they are not independent CrewAI kickoff agents.
_Avoid_: Subagent, crew member

**Automated Review**:
The Reviewer specialist's assessment of generated Content, producing a Reviewer Decision with score, feedback, and safety findings. It is not human approval.
_Avoid_: QA, approval

**Reviewer Decision**:
The automated outcome of an Automated Review: `APPROVED`, `REFINE`, or `REJECTED`. It is distinct from a Human Review Decision.
_Avoid_: Approval, status

**Human Review**:
The human curation gate in which a Principal with write access evaluates Content or an Agent Workflow result and records a Human Review Decision. It is distinct from Automated Review.
_Avoid_: QA, automated review

**Human Review Decision**:
The outcome of a Human Review: `APPROVE`, `REFINE`, or `REJECT`. It is required before Approval when the workflow or Content policy requires human review.
_Avoid_: Reviewer decision, status

**Approval**:
The business state in which Content has passed required Human Review and is accepted for Publication. Approval is not the same as a completed Generation or an automated `APPROVED` decision.
_Avoid_: Review decision, publish

**Publication**:
The delivery of approved Content to an external channel, with channel, scheduled time, and result. Publication is a separate capability from Generation. It is not implemented in the current backend; Creator stops at Approval until a publisher Provider is configured.
_Avoid_: Posting, delivery (unless referring to the Agent Workflow `DELIVERY` step)

**Content Feedback**:
An explicit evaluation of Content by a Principal, optionally linked to the Generation that produced or transformed it, used to improve future Generations. Content Feedback is append-oriented and does not rewrite the evaluated Content.
_Avoid_: Review decision, performance signal

**Performance Signal**:
A post-publication measurement imported from an external channel, such as reach, engagement, or conversion, correlated with Content for learning. It is not a human evaluation and never mutates Content. Performance Signals are future scope.
_Avoid_: Feedback, analytics

**Asset**:
A stored file owned by a Workspace, with type, MIME type, size, checksum, storage location, and lifecycle. An Asset may be linked to a Brand, Project, or Content.
_Avoid_: File, upload, image (when referring to the stored object)

**Brand Asset**:
An Asset owned by a Brand and used as Brand Context, such as a logo, reference image, font, or template.
_Avoid_: Asset (when Brand ownership matters)

**Generated Image**:
A stored image produced by an Image Generation Job, with immutable bytes, MIME type, dimensions, model, prompt, and version. It is a kind of Content artifact.
_Avoid_: Asset, upload, image (when referring to generated output)

**Credit**:
A non-monetary unit consumed by a Generation or Agent Workflow, tracked in an append-only, Workspace-scoped ledger.
_Avoid_: Token, balance, billing unit

**Credit Wallet**:
The Workspace-scoped balance of available Credits, composed of a monthly allowance and purchased Credits.
_Avoid_: Balance, account

**Credit Transaction**:
An append-only ledger entry that changes a Credit Wallet. It records the action, quantity, balance after, idempotency key, and correlation metadata; corrections are new transactions, never edits.
_Avoid_: Payment, invoice, usage record

**Credit Price**:
The configured number of Credits charged for an action key. Credit Prices are global configuration; they are not tenant data.
_Avoid_: Cost, price (when referring to provider cost)

**Provider Usage**:
A record of a Provider call with provider, model, operation, tokens or media units when available, duration, status, and estimated cost. It is technical telemetry, distinct from a Credit Transaction.
_Avoid_: Credit, billing event

**Billing Account**:
The Workspace-scoped commercial account that owns Plans, Subscriptions, payment methods, invoices, and Credit purchases.
_Avoid_: Customer, workspace

**Plan**:
A commercial offering that defines a price and included Credits. A Plan is not a Planning.
_Avoid_: Planning, subscription

**Subscription**:
A Workspace's active commercial relationship to a Plan, including renewal and lifecycle state.
_Avoid_: Plan, membership

**Credit Package**:
A purchasable bundle of Credits. A Credit Package is not a Plan.
_Avoid_: Plan, allowance

**Membership**:
The relationship that grants a Principal a Workspace Role inside one Workspace.
_Avoid_: Global role, permission token

**Workspace Invite**:
A pending, revocable offer to create a Membership in a Workspace with a specified Workspace Role.
_Avoid_: Invitation token, user

**Activity Event**:
An append-oriented business event scoped to a Workspace, optionally to a User, Brand, or entity, used for timeline and audit. It is not technical observability telemetry.
_Avoid_: Log, audit trail (when referring to technical logs)

**Provider**:
An external capability adapter selected behind a stable Creator boundary, such as an AI model, object storage, authentication, or payments.
_Avoid_: Vendor, implementation detail

**Soft Delete**:
The business state in which a resource with a `deleted_at` timestamp remains recoverable in persistence but is excluded from normal reads. Physical purge is a separate operation.
_Avoid_: Hard delete, archive (unless the business behavior differs)

**Campaign**:
A Workspace-scoped marketing initiative with an audience, objectives, a voice, and a time window. A Planning binds to exactly one Campaign.
_Avoid_: Project, plan (the billing concept)

**Persona**:
A Brand-scoped profile of the audience a Campaign addresses: age, gender, main goal, challenge, interests, routine, journey, and trigger.
_Avoid_: Audience, segment, buyer

**Planning**:
A Brand-scoped content plan for a period that binds one Campaign to one Persona, sets volume targets per format (static, carousel, stories), and lists special dates. It contains Post Structures. Planning is the editorial calendar; Calendar refers to its UI view, not a separate entity.
_Avoid_: Calendar (as a separate entity), schedule, editorial plan

**Post Structure**:
The specification of a single post inside a Planning: objective, big idea, main message, headline, call to action, art guidance, format, ratio, and resolution. It originates Content; it is not Content.
_Avoid_: Post, content, template

**Design Structure**:
A one-to-one extension slot attached to a Post Structure, reserved for design parameters. It currently carries no attributes and is retained for contract compatibility.
_Avoid_: Layout, template, design

**Project** (legacy):
A transitional grouping retained for compatibility with existing records and endpoints. New work uses Campaign; Project must not be introduced as a synonym for Campaign.
_Avoid_: Campaign (when referring to the legacy entity)

## Boundaries

- A Workspace owns Brands, legacy Projects, Content, Generations, Generation Jobs, Images, Assets, Brand Knowledge, Credits, Billing Accounts, Campaigns, Personas, Plannings, Agent Workflows, and Activity Events.
- A Brand scopes Brand Context (Brand Settings, brand colors, Brand Assets, Brand Knowledge), Personas, and brand-aligned Generations.
- A Campaign groups the content effort a Planning belongs to; a Planning always references one Campaign and one Persona. Planning is the editorial calendar; there is no separate Calendar entity.
- A Post Structure belongs to a Planning and is workspace-scoped; a Post Structure is a specification, not Content.
- A Briefing is input to a Generation or Agent Workflow; it is not Content and does not create a Content record by itself.
- A Principal reaches Workspace data only through a Membership and its Workspace Role.
- A Generation describes intent. When execution is asynchronous, a Generation Job performs that intent.
- A Content artifact is not an AI provider response: provider output must pass through the application boundary before becoming persisted Content.
- An Agent Workflow is Creator-owned. Replacing CrewAI with another runtime must not change its persisted contracts or Workspace isolation.
- Automated Review and Human Review are distinct. A Human Review Decision is required before Approval when policy requires it; an automated `APPROVED` never substitutes for human approval.
- Publication is a separate capability; the current backend stops at Approval. A Publication record must never be inferred from Generation completion.
- Content Feedback and Performance Signals are append-only inputs to future Generations; they never silently rewrite Content or Brand Context.
- Credit Transactions are append-only; a Credit Wallet balance is derived from its ledger. Provider Usage is telemetry and does not itself change Credits.
- A Project is legacy; new domain work uses Campaign.
- Video, feed/community, media buying, and social publishing are out of current backend scope.
- Design Structure currently carries no attributes; design composition and carousel layout are not implemented by the current Generation boundary.

## Product principles

- **Human concept, AI execution.** The creative concept is human-owned; Creator amplifies it through context, variations, and production capacity.
- **Context over prompts.** Brand consistency comes from structured Brand Context, not from repeating instructions in every prompt.
- **Curation before scale.** Human review and approval are part of the workflow; volume is not a substitute for quality.
- **Governance by default.** Multi-user access, asset history, versions, and Workspace isolation are product requirements, not afterthoughts.
- **Learning loop.** Feedback and performance inform the next cycle without silently rewriting past artifacts.
- **Outcome metrics.** Time saved, rework reduction, approval quality, capacity for variations, and creative leverage are the success metrics; raw output volume is not.

## Implementation status

CONTEXT defines the target vocabulary. Implementation status belongs to `docs/status-do-projeto.md`, the GitHub milestones, and the ADR tracker. Terms marked “future” or “legacy” are not current delivery commitments.
