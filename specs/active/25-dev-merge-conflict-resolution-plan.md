# dev merge conflict resolution plan

## Metadata

| Field | Value |
| --- | --- |
| Date | 2026-05-09 |
| Current branch | `feat/channel-shared-artifacts` |
| Target branch to sync from | `dev` |
| Merge base | `417b5545c86fc85c98621aa8db257c76db76d126` |
| Simulation command | `git merge-tree --name-only HEAD dev` and `git merge-tree --write-tree HEAD dev` |
| Result | 24 conflict files |

This document is a pre-merge decision record. No real `git merge dev` has been
run in the current working tree.

## Summary

Merging `dev` into `feat/channel-shared-artifacts` is the right first step
before merging this large branch back to `dev`. The conflict set is not just
mechanical. It reflects several parallel product and architecture changes:

- `dev` moved authentication toward OAuth setup, Feishu/Lark, single-user mode,
  system admin roles, and admin configuration.
- The current branch added workspace/server collaboration, server channels,
  persistent agents, channel artifacts, channel tasks, activity logs, and
  workspace-scoped collaboration models.
- `dev` added run-scoped replay and runtime environment policy controls, while
  the current branch added channel runtime callback synchronization and
  persistent agent runtime reservation.
- Both branches touched the login UI and i18n keys, but with different auth
  response shapes and provider assumptions.

The high-risk merge areas are backend auth, preset visibility, callback/run
state persistence, task enqueue configuration, and the frontend execution
container.

## Resolved Merge Decisions

The user has reviewed the conflict analysis and made the following merge
decisions. These decisions are the implementation source of truth for the merge
resolution:

- Channel/server collaboration behavior follows the current branch. Preserve the
  callback-driven channel execution placeholder synchronization, status
  projection, and final-message replacement.
- `AgentRun` is added as a supplemental persistence target for callback
  `state_patch`; it must not become the channel projection source of truth in
  this merge.
- Auth uses `dev`'s `single_user | oauth_optional | oauth_required` model, with
  `AUTH_MODE=disabled` kept as a backwards-compatible alias for `single_user`.
- Keep `workspace_features_enabled` in `/auth/config` for this merge.
- System presets are recognized by both `scope == "system"` and
  `user_id == SYSTEM_USER_ID` during the transition.
- Managed system env vars override `.env` model defaults for both normal tasks
  and channel-triggered persistent agents.
- Login no-provider/setup copy should be administrator-facing.
- Keep `frontend/features/task-composer/api/task-submit-api.test.ts` deleted.
- Use `UI_LANG` in `scripts/quickstart.sh`, and use
  `docker compose --profile init up -d rustfs-init` as the RustFS retry command.
- Execution UI keeps `dev`'s run-history pinned behavior when a user selects a
  historical run.

## Conflict Files

| Area | Files |
| --- | --- |
| Backend config and API registration | `backend/.env.example`, `backend/app/api/v1/__init__.py`, `backend/app/core/settings.py`, `backend/app/models/__init__.py` |
| Backend auth and user model | `backend/app/core/deps.py`, `backend/app/repositories/user_repository.py`, `backend/app/schemas/auth.py`, `backend/app/services/auth_service.py` |
| Backend preset visibility | `backend/app/repositories/preset_repository.py`, `backend/app/services/preset_service.py` |
| Backend callback and task execution | `backend/app/services/callback_service.py`, `backend/app/services/task_service.py` |
| Frontend auth/login | `frontend/features/auth/components/login-page-client.tsx`, `frontend/features/auth/lib/paths.ts` |
| Frontend execution/chat | `frontend/features/chat/components/layout/execution-container.tsx`, `frontend/features/chat/services/message-parser.ts` |
| Frontend test lifecycle | `frontend/features/task-composer/api/task-submit-api.test.ts` |
| Frontend i18n | `frontend/lib/i18n/locales/de/translation.json`, `frontend/lib/i18n/locales/en/translation.json`, `frontend/lib/i18n/locales/fr/translation.json`, `frontend/lib/i18n/locales/ja/translation.json`, `frontend/lib/i18n/locales/ru/translation.json`, `frontend/lib/i18n/locales/zh/translation.json` |
| Dev script | `scripts/quickstart.sh` |

## Decision Areas

### 1. Auth mode: local workspace user vs dev auth system

Conflicts:

- `backend/.env.example`
- `backend/app/core/settings.py`
- `backend/app/core/deps.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/auth_service.py`
- `frontend/features/auth/components/login-page-client.tsx`
- `frontend/features/auth/lib/paths.ts`
- all login i18n files

Current branch adds:

- `AUTH_MODE` with `disabled | oauth_required`
- `WORKSPACE_FEATURES_ENABLED`
- `AUDIT_RULES`
- `LOCAL_DEFAULT_USER_ID`
- `LOCAL_DEFAULT_USER_NAME`
- `AuthConfigResponse.auth_mode`
- `AuthConfigResponse.workspace_features_enabled`
- local disabled-auth user creation through `get_or_create_local_user`
- login UI assuming `google | github` provider strings

`dev` adds:

- `AUTH_MODE` with `oauth_required | oauth_optional | single_user`
- `SINGLE_USER_ID`
- `SINGLE_USER_NAME`
- `SYSTEM_ADMIN_EMAILS`
- Feishu/Lark OAuth settings
- `CurrentUserResponse.system_role`
- provider status objects and `configured_providers`
- `setup_required` and `single_user_effective`
- `ensure_single_user`
- admin-role resolution
- login UI driven by provider config, loading state, setup-required state, and
  Feishu/Lark copy

Conflict nature:

The branches define different auth mental models. Current branch treats
disabled auth as a local fallback user and exposes workspace feature flags
through auth config. `dev` treats local usage as `single_user`, supports
optional/required OAuth, and introduces system admin authorization.

Recommended resolution:

- Use the `dev` auth model as the base because it is broader and supports
  admin/runtime management.
- Preserve the current branch's workspace and audit settings, but do not keep
  `LOCAL_DEFAULT_USER_ID` / `LOCAL_DEFAULT_USER_NAME` as a second local-user
  concept unless explicitly needed.
- Map old `auth_mode == "disabled"` behavior to `single_user` if backwards
  compatibility is required.
- Add `workspace_features_enabled` to the auth config only if frontend still
  consumes it after the merge; otherwise keep it as backend settings only.
- Frontend login should follow `dev`'s provider-status contract and keep a
  translated no-provider empty state.

Resolved decision:

- Use `single_user` as the formal local auth mode and support
  `AUTH_MODE=disabled` as a backwards-compatible alias.
- Keep `workspace_features_enabled` in `/auth/config` for this merge; record
  moving it to a dedicated product/runtime config endpoint as follow-up work.

### 2. Preset visibility: workspace scoped presets vs system presets

Conflicts:

- `backend/app/repositories/preset_repository.py`
- `backend/app/services/preset_service.py`

Current branch adds:

- `Preset.scope`
- `Preset.workspace_id`
- visibility by user or active `WorkspaceMember`
- `require_workspace_member`

`dev` adds:

- `SYSTEM_USER_ID`
- system-user-owned presets visible to all users
- `include_deleted`
- `get_visible_by_id(..., system_user_id=...)`

Conflict nature:

Both branches extend preset visibility, but around different ownership models:
workspace membership vs global system presets. Choosing either side directly
would drop a real feature.

Recommended resolution:

- Combine visibility as a union:
  - user-owned presets
  - system presets or presets owned by `SYSTEM_USER_ID`
  - workspace presets where the current user is an active workspace member
- Preserve `include_deleted` for admin/system surfaces.
- Keep service-level workspace membership checks for create/update operations.

Resolved decision:

- Recognize system presets by both `scope == "system"` and
  `user_id == SYSTEM_USER_ID` during the transition.
- Preserve workspace-scoped visibility in the same visible preset API so the
  merge does not split the existing UI contract.

### 3. Callback state: channel placeholder sync vs run-scoped state patch

Conflict:

- `backend/app/services/callback_service.py`

Current branch adds:

- synchronization from executor callback into server-channel execution
  placeholder messages
- replacement of run placeholders with final channel messages

`dev` adds:

- writes `callback.state_patch` into both session and `AgentRun`
- run-scoped replay/history support

Conflict nature:

Current branch makes server channels reflect execution progress. `dev` makes
run records independently replayable. They are complementary, but a naive
resolution can lose either final channel message projection or run replay data.

Recommended resolution:

- First persist the state patch to `AgentSession`.
- If `db_run` exists, also persist the same patch to `AgentRun`.
- Keep the current branch's channel placeholder synchronization for running,
  completed, and failed callbacks.
- Verify that any final-message replacement uses the run id when available.

Resolved decision:

- Keep server-channel message projection as the current branch's callback-driven
  side effect for this merge.
- Also persist callback `state_patch` to `AgentRun` when a run exists, so
  `dev`'s run-scoped replay data is not lost.
- Record the longer-term `AgentRun`-as-fact-source direction in
  `specs/research/2026-05-09-dev-merge-compromises-and-evolution-research.md`.

### 4. Task enqueue: runtime env policy vs persistent agent runtime

Conflict:

- `backend/app/services/task_service.py`

Current branch adds:

- `logger`
- persistent agent runtime reservation through `AgentRuntimeService`
- agent runtime mode handling for persistent channel agents

`dev` adds:

- `EnvVarService`
- system env map lookup for `DEFAULT_MODEL` and `MODEL_LIST`
- runtime environment policy integration

Conflict nature:

The conflict hunk is small (`logger` vs `env_var_service`), but the surrounding
behavior is important. The current branch reserves persistent agent runtime;
`dev` centralizes model defaults and runtime env policy through managed env
vars.

Recommended resolution:

- Keep both `logger = logging.getLogger(__name__)` and
  `env_var_service = EnvVarService()`.
- Use `dev`'s system env map for model defaults and model list validation.
- Preserve current branch runtime reservation logic.
- After merge, test enqueue flows for normal tasks and persistent channel-agent
  tasks.

Resolved decision:

- Managed system env vars override `.env` defaults for all enqueue paths,
  including server-channel triggered persistent agents.

### 5. Backend registration: collaboration APIs vs admin/runtime policy APIs

Conflicts:

- `backend/app/api/v1/__init__.py`
- `backend/app/models/__init__.py`

Current branch adds:

- server, channel, channel task, activity log, workspace, invite, and agent
  identity models/routes

`dev` adds:

- admin API registration
- `RuntimeEnvPolicy` model registration

Conflict nature:

This is mostly additive. The real risk is dropping imports, which can break
router registration, Alembic autogeneration, or SQLAlchemy relationship setup.

Recommended resolution:

- Keep both sets of imports and `__all__` exports.
- After merge, run backend import/compile checks and at least the auth,
  runtime-env-policy, server-channel, and task service tests.

Decision needed:

- None expected unless API ordering or admin route exposure needs to be gated.

### 6. Execution UI: channel panel reset vs run history timeline

Conflict:

- `frontend/features/chat/components/layout/execution-container.tsx`

Current branch adds:

- right-panel collapse state reset on session changes
- branch-specific handling around artifacts/computer tabs

`dev` adds:

- run list loading
- selected run state
- pinned-to-history state
- legacy replay availability
- run-scoped tool execution polling
- mobile run timeline props

Conflict nature:

`dev` significantly rewired execution UI around run history. Current branch has
a smaller but still relevant right-panel behavior change. Choosing current would
lose run-scoped replay UI; choosing `dev` blindly may regress right-panel
collapse defaults.

Recommended resolution:

- Use `dev`'s run-history structure as the base.
- Preserve current branch's right-panel collapse reset:
  `setIsRightPanelCollapsed(defaultRightPanelCollapsed)`.
- Include `defaultRightPanelCollapsed` in the relevant effect dependency list.
- Verify desktop and mobile execution views after merge.

Resolved decision:

- Preserve `dev`'s run-history pinned behavior: when a user selects a historical
  run, the UI should not automatically jump back to the latest run.

### 7. Message parser import boundary

Conflict:

- `frontend/features/chat/services/message-parser.ts`

Current branch imports `AgentTriggerContext` from the feature public type
surface. `dev` imports from `../types/index.ts`.

Conflict nature:

This is a frontend boundary/style conflict, not a semantic feature conflict.

Recommended resolution:

- Prefer the project alias/public surface import if it still exports all needed
  types: `@/features/chat/types`.
- Avoid explicit `.ts` extension in TypeScript imports unless the project
  config requires it.

Decision needed:

- None expected.

### 8. Deleted test vs modified test

Conflict:

- `frontend/features/task-composer/api/task-submit-api.test.ts`

Current branch deleted this file in commit
`4aed5259 chore(frontend): remove stale unit tests and add yesterday i18n key`.
`dev` modified the same test for task submission API changes.

Conflict nature:

This is a modify/delete conflict. The decision is whether the test was truly
stale or whether `dev`'s changed API contract still needs coverage.

Recommended resolution:

- Re-open the test during merge and compare it with the current task submit API.
- If the test covers still-valid behavior, keep and update it.
- If it only encodes removed behavior, keep the deletion and make sure related
  coverage exists elsewhere.

Resolved decision:

- Keep `frontend/features/task-composer/api/task-submit-api.test.ts` deleted.
- If task submit coverage is later needed, add a fresh test based on the current
  API rather than resurrecting the stale file during this merge.

### 9. Login i18n keys

Conflicts:

- all six `frontend/lib/i18n/locales/*/translation.json` files

Current branch adds:

- more explicit `noProviders` copy that points users to backend OAuth settings

`dev` adds:

- `loading`
- `setupRequiredTitle`
- `setupRequiredDescription`
- `setupRequiredHint`
- `feishu`
- `subtitleSingle`
- `providers.{google,github,feishu}`
- a shorter no-provider message in some locales

Conflict nature:

This follows the auth model conflict. The keys are not mutually exclusive; the
merged UI likely needs all of them.

Recommended resolution:

- Keep all `dev` setup/loading/provider keys.
- Keep a `noProviders` key in every locale.
- Align no-provider copy with the final auth decision:
  - if OAuth setup is admin-managed, use `setupRequired*` for required setup and
    reserve `noProviders` for optional/no available providers;
  - if users are expected to edit backend env vars directly, keep the current
    more explicit backend settings wording.

Resolved decision:

- Use administrator-facing login setup/no-provider copy.

### 10. quickstart language variable and init retry command

Conflict:

- `scripts/quickstart.sh`

Current branch adds:

- warnings for Docker GID, RustFS directory ownership/permission, model API key,
  and Anthropic default model
- retry text using `docker compose --profile init rm -fsv rustfs-init && docker
  compose --profile init run --rm --no-deps rustfs-init`

`dev` adds:

- rename from `LANG` to `UI_LANG`
- retry text using `docker compose --profile init up -d rustfs-init`

Conflict nature:

The `LANG` variable name can collide with the shell locale environment. `dev`
renamed it to `UI_LANG`, which is safer. The RustFS retry command changed
semantics and needs one chosen operational path.

Recommended resolution:

- Use `UI_LANG`.
- Keep all warning keys from both branches.
- Prefer the retry command that matches the current compose init profile after
  checking the compose service behavior.

Resolved decision:

- Use `docker compose --profile init up -d rustfs-init` for the retry command.
- Use `UI_LANG` rather than `LANG` for script UI language branching.

## Proposed Merge Order

1. Resolve backend config/auth first, because it affects frontend API contracts.
2. Resolve preset visibility and backend registration next.
3. Resolve callback/task service runtime behavior.
4. Resolve frontend auth UI and i18n after the backend auth response shape is
   chosen.
5. Resolve execution container and message parser.
6. Resolve `task-submit-api.test.ts` after checking current task submit API.
7. Resolve `scripts/quickstart.sh` last after checking compose init behavior.

## Suggested Verification After Resolution

Backend:

```bash
cd backend
uv run python -m py_compile app/**/*.py
uv run pytest tests/test_auth_service.py tests/test_task_service.py tests/test_runtime_env_policy_service.py
uv run pytest tests/test_server_channel_message_service.py tests/test_channel_runtime_service.py
```

Frontend:

```bash
cd frontend
pnpm lint
pnpm build
```

Manual flows:

- Login config endpoint and login page with no providers, one provider, and
  multiple providers.
- Single-user local startup.
- Admin/runtime env policy page if kept from `dev`.
- Create a normal task and verify run-scoped replay.
- Trigger a server-channel persistent agent and verify channel placeholder to
  final-message synchronization.
- Open artifacts/computer panels on desktop and mobile.

## Resolved Decision Checklist

- [x] Use `single_user` as the formal local auth mode and keep `disabled` as an
      alias.
- [x] Keep `workspace_features_enabled` in auth config for this merge.
- [x] Represent system presets by both `scope == "system"` and
      `SYSTEM_USER_ID` during the transition.
- [x] Show workspace presets in the same visible preset list as system/user
      presets.
- [x] Keep callback-driven channel execution projection as the current merge
      behavior; persist `AgentRun.state_patch` as supplemental run data.
- [x] Let managed system env vars override `.env` defaults for all task enqueue
      paths.
- [x] Keep `dev`'s run-history pinned behavior.
- [x] Keep `task-submit-api.test.ts` deleted.
- [x] Use administrator-facing login setup/no-provider copy.
- [x] Retry `rustfs-init` with `docker compose --profile init up -d rustfs-init`.
