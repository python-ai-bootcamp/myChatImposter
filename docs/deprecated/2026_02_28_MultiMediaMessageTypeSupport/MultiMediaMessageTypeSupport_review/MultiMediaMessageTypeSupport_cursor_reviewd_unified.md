# Unified Review: `MultiMediaMessageTypeSupport.md`

This is a consolidated review of:
- `docs/MultiMediaMessageTypeSupport.md`
- `docs/MultiMediaMessageTypeSupport_cursor_reviewd.md`
- `docs/MultiMediaMessageTypeSupport_cursor_reviewd_composer_1_5.md`
- `docs/MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md`
- `docs/MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md`

Only serious, implementation-critical points are kept below.

---

## Prioritized Issues (Most Important First)

| Rank | Importance | Point | Why It Is Serious | Source Review Files | Details |
|---|---|---|---|---|---|
| 1 | Critical | Persistence-first contract is self-contradictory | Can produce abandoned/stuck jobs and data-loss-like behavior across restarts | `MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md` | [P1](#p1-persistence-first-contract-is-self-contradictory) |
| 2 | Critical | `update_message_by_media_id` is underspecified | Easy to corrupt queue limits and callback behavior | `MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md` | [P2](#p2-update_message_by_media_id-contract-is-missing-critical-rules) |
| 3 | Critical | Eviction rewrite is incomplete | Can infinite-loop or over-evict valid messages | `MultiMediaMessageTypeSupport_cursor_reviewd.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_composer_1_5.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md` | [P3](#p3-placeholder-protected-eviction-logic-is-incomplete) |
| 4 | High | Service ownership/lifecycle wiring is undefined | Feature may never run correctly even if code exists | `MultiMediaMessageTypeSupport_cursor_reviewd.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_composer_1_5.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md` | [P4](#p4-mediaprocessingservice-lifecycle-and-wiring-are-not-defined) |
| 5 | High | Node/media infrastructure assumptions do not match repo | Spec references config/volume/UID flow not present in current stack | `MultiMediaMessageTypeSupport_cursor_reviewd_composer_1_5.md`, `MultiMediaMessageTypeSupport_cursor_reviewd.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md` | [P5](#p5-node-and-infrastructure-assumptions-do-not-match-current-code) |
| 6 | High | Provider payload contract is not strict enough | Node/Python drift risk; media metadata can be silently dropped | `MultiMediaMessageTypeSupport_cursor_reviewd.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_composer_1_5.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md` | [P6](#p6-node--python-message-contract-needs-an-explicit-schema) |
| 7 | High | Recovery ID sequencing is not fully defined | Placeholder reinjection can collide with future message IDs | `MultiMediaMessageTypeSupport_cursor_reviewd_gpt_5_3_codex.md`, `MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high.md` | [P7](#p7-recovery-seeding-can-break-message-id-monotonicity) |

---

## Detailed Findings

### P1. Persistence-first contract is self-contradictory

The spec prose says workers persist result first (`status="completed"` + `result`) and only then attempt in-memory queue delivery.  
But the included `BaseMediaProcessor.process_job` pseudocode updates queue first and DB state second, and also returns early when no active bot queue is found.

Why this matters:
- If queue update happens first and process crashes before DB update, recovery has inconsistent state.
- If worker returns early because bot is offline, job can remain in `processing` until cleanup, instead of being persisted for reaping.

Concrete amendment:
- Define one required order: **claim -> process -> persist result in active/holding -> attempt in-memory delivery -> delete/move job**.
- Remove/replace early return on missing active `BotQueuesManager`; offline bots must still get DB-persisted completed jobs for reaping.

---

### P2. `update_message_by_media_id` contract is missing critical rules

This method is central to the design and referenced throughout the spec, but behavior is not fully defined.

Current queue behavior (`queue_manager.py`) relies on `_total_chars` correctness for retention/eviction.  
If placeholder content changes from caption/empty to long transcript and `_total_chars` is not updated exactly, limits become wrong.

Concrete amendment:
- Specify method contract explicitly:
  1. locate by `media_processing_id`
  2. compute old/new sizes
  3. update `content`, `message_size`, clear `media_processing_id`
  4. update `_total_chars = _total_chars - old_size + new_size`
  5. fire callbacks exactly once
  6. return structured result (`updated`, `not_found`, etc.)

Example:
- Placeholder `content=""` (0 chars) becomes transcript of 1800 chars.
- `_total_chars` must increase by exactly `+1800`; otherwise eviction math is wrong.

---

### P3. Placeholder-protected eviction logic is incomplete

The spec correctly identifies that naive `popleft()` is unsafe for protected placeholders, but the proposed rewrite still misses edge behavior.

Required policy clarification:
- Protected placeholders are **completely excluded** from queue-limit evaluation.
- Limits (`max_messages`, `max_characters`, age-based retention) apply only to the **unprotected subset**.
- Therefore, protected placeholders are ignored both for "can this message be evicted?" and for "is the queue currently over limit?" checks.

Behavior implication:
- A queue containing only protected placeholders should not trigger eviction work by itself.
- Eviction decisions are made only against unprotected messages; if none exist, eviction simply does nothing and processing continues.

Concrete amendment:
- Define limit calculations and eviction on unprotected messages only:
  - compute effective queue size/chars/age using only `media_processing_id is None` messages
  - keep placeholders fully non-evictable and fully excluded from limit arithmetic
  - evict oldest eligible unprotected message(s) only when the unprotected subset exceeds limits

---

### P4. `MediaProcessingService` lifecycle and wiring are not defined

Spec describes service behavior, but not exact ownership/wiring in this codebase.

Current architecture:
- Active sessions are in `GlobalStateManager.active_bots` and `GlobalStateManager.chatbot_instances`.
- `BotQueuesManager` instances live inside `SessionManager`.
- `main.py` lifespan currently initializes actionable queue manager, not media processor manager.

Concrete amendment:
- Define where media service is created/stored/started/stopped (same lifecycle clarity as existing queue manager).
- Define resolver API for `bot_id -> BotQueuesManager` using `GlobalStateManager`.
- Define where hourly cleanup is scheduled and how singleton scheduling is guaranteed.

---

### P5. Quota retrieval path and infra rollout need explicit implementation rules

The spec already defines the quota source of truth (`media_storage_quota_gb` in configuration collection).  
The implementation should explicitly use this runtime retrieval path:
- backend reads quota from MongoDB and passes it to Node in `/initialize` payload.

This is not a design change request; it is a wording/contract clarification request.
Locking this path in the spec avoids implementation drift and keeps Node stateless regarding DB config access.

Additionally, the spec introduces required infra changes (shared media volume and UID/GID runtime user mapping).  
These are valid **to-be-implemented requirements**; the review point is only to make them explicit and unmissable in the spec.

Concrete amendment:
- Add explicit sentence in spec: backend resolves `media_storage_quota_gb` from DB and includes it in `/initialize`; Node does not read this value directly from MongoDB.
- Add explicit sentence in spec: `scripts/start.sh` must export `CURRENT_UID` and `CURRENT_GID` into `.env` before `docker compose up`, and both `backend` and `whatsapp_baileys_server` must run with `user: "${CURRENT_UID}:${CURRENT_GID}"`.

---

### P6. Node <-> Python message contract needs an explicit schema

Spec says media metadata is sent, but contract is still too implicit.

Clarification: this is a **wire contract** concern, not only an internal Python model concern.
The message crosses a runtime boundary (Node.js -> WebSocket JSON -> Python), so field names/types/requiredness must be explicit at the payload level.
An internal Python model is still recommended, but it should validate the already-defined WS payload contract rather than replace it.

Current provider (`chat_providers/whatsAppBaileys.py`) expects `msg['message']` and calls `BotQueuesManager.add_message(...)`.  
Current manager signature also includes `correspondent_id` first, which the spec function signature snippet omits.

Concrete amendment:
- Define strict WS payload schema for:
  - text message
  - media message
  - corrupt media message
- For each payload, mark fields as required/optional and define type/nullability.
- Keep caption in `message` field (or clearly rename and update both sides consistently).
- Correct method signature examples to match actual API shape (`correspondent_id` required).

---

### P7. Recovery seeding can break message ID monotonicity

Spec requires reinjecting placeholder messages with original IDs during recovery (`inject_placeholder`).  
But queue ID initialization today uses last persisted DB message ID. Re-injected placeholders may have higher IDs than DB max.

Risk:
- New messages after recovery can reuse IDs unless next-id is corrected.

Concrete amendment:
- After reinjection, force:
  - `next_id = max(next_id, max(injected_placeholder_ids) + 1)`
- Add DB safety net on `queues`: unique compound index on (`bot_id`, `provider_name`, `correspondent_id`, `id`).
  (Do not use unique index on `id` alone, because `id` is not globally unique.)

Example:
- DB max id = 40, reinjected placeholders include ids 41, 42.
- Next new incoming message must become 43, not 41.

---

## What Was Intentionally Excluded (Chaff)

The following recurring points from prior reviews were excluded from the unified critical list because they are lower-impact or optional for Phase 1:
- optional observability improvements (extra metrics endpoints, UI counters)
- optional retry policy tuning for external APIs
- documentation housekeeping (`CLAUDE.md` refresh)
- platform commentary that does not change core design correctness
- stylistic wording-only edits that do not alter behavior

---

## Final Conclusion

The spec direction is strong, but the seven items above must be clarified/fixed before implementation to avoid correctness failures in queue behavior, job lifecycle, and crash recovery.  
If these are resolved, the design becomes implementation-safe and aligns well with the current architecture.
