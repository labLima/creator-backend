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

## Boundaries

- A Workspace owns Brands, Projects, Content, Generations, Generation Jobs, Images, Assets, Brand Knowledge, Credits, and Agent Workflows.
- A Brand scopes Brand Settings, Brand Knowledge, and brand-aligned Generations.
- A Principal reaches Workspace data only through a Membership and its Workspace Role.
- A Generation describes intent. When execution is asynchronous, a Generation Job performs that intent.
- A Content artifact is not an AI provider response: provider output must pass through the application boundary before becoming persisted Content.
- An Agent Workflow is Creator-owned. Replacing CrewAI with another runtime must not change its persisted contracts or Workspace isolation.
