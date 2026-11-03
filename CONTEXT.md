# Creator

Creator is a multi-tenant platform for planning, generating, reviewing, and managing marketing content with AI assistance.

## Language

**Creator**:
The application as a whole. It contains several business capabilities and is not the name of an individual workflow or generated artifact.
_Avoid_: Create Bloom, Creator Bloom

**Workspace**:
The tenant boundary that owns business data, memberships, permissions, usage, and generated artifacts.
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
The marketing identity owned by a Workspace. It scopes Brand Settings, Brand Knowledge, and brand-aligned Generations.
_Avoid_: Client, company, account

**Brand Knowledge**:
Workspace- and Brand-scoped source material used as retrieval context for Generations and agent workflows.
_Avoid_: RAG data, vector store, document

**Content**:
A persisted marketing artifact produced or managed by Creator, such as copy, an image, or a video. It is the output of a workflow, not the workflow itself.
_Avoid_: Creator, generation, job

**Generation**:
A request to an AI provider to produce or transform Content for a Workspace. A Generation may complete synchronously; when execution is asynchronous, a Generation Job performs it.
_Avoid_: Content, job, task

**Generation Job**:
The durable asynchronous execution of a Generation, including its lifecycle, attempts, result, and failure information.
_Avoid_: Generation, request, queue message

**Artifact Type**:
The kind of output a Generation Job produces: `IMAGE`, `COPY`, or `CAPTION`.
_Avoid_: Content type, media type

**Generation Operation**:
The intent of a Generation Job: `CREATE`, `REGENERATE`, or `TRANSFORM`.
_Avoid_: Action, mode

**Agent Workflow**:
A durable multi-step Generation executed by specialist roles and persisted as runs and steps. Creator owns its state transitions; CrewAI is an adapter, not the workflow engine.
_Avoid_: Crew, pipeline, job

**Credit**:
A non-monetary unit consumed by a Generation or Agent Workflow, tracked in an append-only, Workspace-scoped ledger.
_Avoid_: Token, balance, billing unit

**Membership**:
The relationship that grants a Principal a Workspace Role inside one Workspace.
_Avoid_: Global role, permission token

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
A Brand-scoped content plan for a period that binds one Campaign to one Persona, sets volume targets per format (static, carousel, stories), and lists special dates. It contains Post Structures.
_Avoid_: Calendar, schedule, editorial plan

**Post Structure**:
The specification of a single post inside a Planning: objective, big idea, main message, headline, call to action, art guidance, format, ratio, and resolution. It originates Content; it is not Content.
_Avoid_: Post, content, template

**Design Structure**:
A one-to-one extension slot attached to a Post Structure, reserved for design parameters. It currently carries no attributes and is retained for contract compatibility.
_Avoid_: Layout, template, design

## Boundaries

- A Workspace owns Brands, Projects, Content, Generations, Generation Jobs, Images, Assets, Brand Knowledge, Credits, Campaigns, Personas, Plannings, and Agent Workflows.
- A Brand scopes Brand Settings, Brand Knowledge, Personas, and brand-aligned Generations.
- A Campaign groups the content effort a Planning belongs to; a Planning always references one Campaign and one Persona.
- A Post Structure belongs to a Planning and is workspace-scoped; a Post Structure is a specification, not Content.
- A Principal reaches Workspace data only through a Membership and its Workspace Role.
- A Generation describes intent. When execution is asynchronous, a Generation Job performs that intent.
- A Content artifact is not an AI provider response: provider output must pass through the application boundary before becoming persisted Content.
- An Agent Workflow is Creator-owned. Replacing CrewAI with another runtime must not change its persisted contracts or Workspace isolation.
