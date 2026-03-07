# MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md — Deep Spec Review and Action Plan

## Scope

This review is based on:
- `docs/MultiMediaMessageTypeSupport.md` (full deep read, then second pass after code study)
- Current implementation in:
  - `queue_manager.py`
  - `services/ingestion_service.py`
  - `services/session_manager.py`
  - `services/bot_lifecycle_service.py`
  - `chat_providers/whatsAppBaileys.py`
  - `chat_providers/whatsapp_baileys_server/server.js`
  - `main.py`
  - `dependencies.py`
  - `infrastructure/db_schema.py`
  - relevant tests in `tests/test_queue_manager.py` and `tests/test_refactored_services.py`

---

## Executive assessment

The spec has a strong direction (async placeholder model + persistence-first lifecycle + holding/active symmetry), and it correctly identifies the biggest current behavioral bug (`IngestionService.stop()` final drain issue).

However, in its current form it is **not yet implementation-safe**. There are several critical gaps where the spec references behaviors/methods/components that do not yet exist and does not fully define their contracts under race conditions. If implemented "as-is", this can cause:
- duplicate or lost callbacks
- stale/infinite placeholders
- queue memory accounting drift
- stuck jobs in processing state
- provider/backend payload mismatch

---

## High-severity design gaps / errors

### 1) Missing concrete ownership/wiring of `MediaProcessingService`

**Gap:** Spec says workers poll `media_processing_jobs` and route back to `Dict[str, BotQueuesManager]`, but current architecture exposes active bots as:
- `GlobalStateManager.active_bots` (bot_id -> instance_id)
- `GlobalStateManager.chatbot_instances` (instance_id -> `SessionManager`)
- queue manager nested at `SessionManager.bot_queues_manager`

There is no central `Dict[bot_id, BotQueuesManager]`.

**Risk:** Implementation divergence and race bugs while resolving queue references.

**Required spec fix:**
- Define a single resolver API (example): `get_bot_queues(bot_id) -> Optional[BotQueuesManager]`.
- Define who owns worker startup/shutdown (likely app-level in `main.py` lifespan, similar to `AsyncMessageDeliveryQueueManager`).

---

### 2) `update_message_by_media_id()` is critical but under-specified

Spec depends heavily on this method but only describes intent.

**Current reality:** `CorrespondentQueue` has no such method. Also `_total_chars` enforcement is central.

**Risk:** easy to update `content/message_size` but forget `_total_chars`, causing retention corruption and limit violations.

**Required spec fix (explicit contract):**
- Inputs: `(correspondent_id, media_processing_id, new_content)`
- Behavior:
  1. locate message by `media_processing_id`
  2. compute `old_size`, `new_size`
  3. update `content`, `message_size`, set `media_processing_id=None`
  4. update `_total_chars = _total_chars - old_size + new_size`
  5. enforce `max_characters_single_message` policy decision (truncate or preserve; must be explicit)
  6. trigger callbacks exactly once
- Return value should indicate `{updated: bool, reason: ...}` for worker decisions.

---

### 3) Placeholder eviction rewrite is conceptually right but operationally incomplete

Spec correctly spots the `popleft()` flaw in `_evict_while`, but does not define edge behavior when all messages are protected placeholders.

**Risk:** either infinite loop or unbounded queue growth.

**Required spec fix:**
- Define deterministic fallback when no evictable message exists:
  - option A: reject new incoming non-placeholder message with explicit log + metric
  - option B: permit temporary overflow with bounded cap + alert
- Must state this explicitly for age/char/count eviction paths.

---

### 4) Bot startup recovery can collide with `_next_message_id` sequence

Spec injects old placeholders with original IDs (`inject_placeholder`) while current queue initializes `_next_message_id` from DB max id.

**Risk:** ID collision or monotonicity regression after recovery injection + new messages.

**Required spec fix:**
- After injecting placeholders, queue must set `_next_message_id = max(current_next, max(injected_ids)+1)`.

---

### 5) Worker state transitions around stop/restart are not fully crash-safe

Spec has good persistence-first intent but still leaves ambiguity for jobs in `processing` when bot stops or worker disappears.

**Risk:** jobs marooned in `processing` until hourly cleanup (high latency).

**Required spec fix:**
- Define heartbeat/lease semantics for processing claims (e.g., `claimed_at`, `worker_id`, `lease_timeout_seconds`).
- Reclaim timed-out `processing` jobs back to `pending` before 3-hour cleanup window.

---

### 6) Node quota mechanism uses Unix `du` and undeclared `botConfig`

Spec snippet assumes:
- `du -sm` exists in runtime image
- `botConfig` is available in `processMessage`

In current `server.js`, this is not established in the shown flow.

**Risk:** runtime failures on missing command/context + blocking behavior ambiguity.

**Required spec fix:**
- Define quota source in Node clearly (where loaded, cached, refresh cadence).
- Prefer `fs.statfs` or a pure Node directory-size strategy with timeout over shelling out to `du`.

---

## Medium-severity risks / ambiguities

### 7) Callback semantics can break conversational ordering expectations

Spec intentionally allows out-of-order callback completion for media vs text. This is accepted, but not operationally mitigated.

**Risk:** user sees bot replying to later text before earlier media transcript context.

**Enhancement:** optional per-correspondent "media gating mode" (off by default) for stricter conversational ordering when desired.

---

### 8) Payload contract between Node and Python should be explicitly versioned

Spec describes fields but not a strict schema or examples. Current provider expects `msg['message']` and currently ignores media metadata fields.

**Risk:** silent drops when Node/Python drift.

**Enhancement:**
- Add explicit WebSocket payload examples for:
  - text message
  - media success metadata
  - media-corrupt metadata
- Add a protocol version field (`payload_version`).

---

### 9) Missing DB indexes for new media job collections

Spec does not list required indexes. `infrastructure/db_schema.py` currently has none for these collections.

**Risk:** worker poll slowdown and expensive lifecycle transitions.

**Enhancement (minimum):**
- `media_processing_jobs`: `(status, mime_type, created_at)`, `(bot_id)`, `(guid unique?)`
- `media_processing_jobs_holding`: `(bot_id, status)`, `(guid unique?)`
- `media_processing_jobs_failed`: `(created_at)`, `(bot_id)`, `(error)`

---

### 10) Cleanup ownership and scheduler integration are undefined

Spec says hourly cleanup scans all queues/jobs but not where it runs.

**Risk:** duplicate schedulers or none at all.

**Enhancement:** define exact owner (likely backend app lifespan scheduler) and singleton guarantee.

---

## Positive design points (keep)

- Provider-agnostic queue-level integration point is correct.
- Suppressing callbacks for placeholders and firing on completion is correct for `AutomaticBotReplyService`.
- Persistence-first ("write result to DB before in-memory delivery") is the right failure model.
- Holding/active lifecycle mirroring `AsyncMessageDeliveryQueueManager` is a solid mental model.
- Explicit corrupt and unsupported processors are excellent for operator visibility.

---

## Required spec amendments before implementation starts

1. **Define new APIs precisely**
   - `CorrespondentQueue.inject_placeholder`
   - `CorrespondentQueue.pop_ready_message`
   - `CorrespondentQueue.update_message_by_media_id`
   - return values + failure modes

2. **Define lifecycle owner components**
   - where `MediaProcessingService` is started/stopped
   - where hourly cleanup is registered
   - how workers access bot queues via `GlobalStateManager`

3. **Define strict data contracts**
   - WS payload schema examples
   - job document schema (including timestamps/lease fields)
   - `Message` dataclass changes and backward compatibility notes

4. **Define retention and overflow behavior**
   - what happens when queue has only protected placeholders and limits are exceeded

5. **Define index + migration plan**
   - new collections + indexes
   - startup migration logic for old records (if any)

6. **Define timeout/reclaim behavior**
   - processor call timeout policy
   - processing lease expiration and reclamation

---

## Proposed implementation plan (phased)

### Phase 0 — Spec hardening (must-do first)
- Apply all "Required spec amendments" above.
- Add one sequence diagram for:
  - normal media flow
  - bot stop during processing
  - recovery/reaping on reconnect

### Phase 1 — Queue + ingestion primitives
- Extend `Message` with `media_processing_id`.
- Implement `inject_placeholder`, `pop_ready_message`, `update_message_by_media_id`.
- Replace ingestion `pop_message()` loop with `pop_ready_message()` + final drain in `stop()`.
- Add unit tests for eviction/skip-pop/callback semantics.

### Phase 2 — Provider payload and placeholder injection
- Node `server.js`: detect media types, stream to shared volume, emit metadata payload.
- Python `whatsAppBaileys.py`: pass media metadata into `BotQueuesManager.add_message`.
- `BotQueuesManager.add_message`: enqueue placeholder + create media job document.

### Phase 3 — MediaProcessingService + processors
- Implement worker pools by mime routing config.
- Implement base processor lifecycle + timeout wrappers.
- Implement stub processors first (as spec suggests), then real APIs.

### Phase 4 — Lifecycle/recovery/cleanup
- Startup move active->holding + reset orphan `processing` claims.
- Bot start re-seed placeholders from holding, reap completed, reactivate pending.
- Bot stop move active jobs to holding.
- Hourly cleanup for stale placeholders/jobs + media file deletion.

### Phase 5 — Observability + operations
- Add metrics/logs: queue depth by pool, claim/complete latencies, failed reasons.
- Add operator endpoints (optional) for failed job retry/requeue.

---

## Test plan additions (critical)

- `CorrespondentQueue`:
  - placeholder insert does not callback
  - completion update callbacks exactly once
  - `_total_chars` remains correct after update
  - eviction with mixed placeholder/non-placeholder
  - all-placeholder overflow behavior

- `IngestionService`:
  - regular cycle persists only ready messages
  - `stop()` final drain persists ready + leaves placeholders

- Provider integration:
  - media payload schema compatibility Node -> Python
  - corrupted/unsupported mime routes

- Lifecycle:
  - bot stop/start with pending and completed jobs
  - worker result persistence when bot disappears
  - reclaim of stale `processing` claims

---

## Final recommendation

Proceed with this feature, but only after the spec is tightened on the six critical points above. The architecture direction is good; the main remaining risk is **contract ambiguity** across queue semantics, lifecycle ownership, and race handling. Once those are made explicit, implementation is straightforward and testable.

