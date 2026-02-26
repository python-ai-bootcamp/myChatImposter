# MultiMediaMessageTypeSupport_cursor_reviewd_opus_4_6_high — Deep Spec Review

Review of `MultiMediaMessageTypeSupport.md` against the live codebase (`queue_manager.py`, `ingestion_service.py`, `async_message_delivery_queue_manager.py`, `whatsAppBaileys.py`, `server.js`, `session_manager.py`, `bot_lifecycle_service.py`, `main.py`, `dependencies.py`, `config_models.py`, `automatic_bot_reply/service.py`).

---

## 1. Executive Summary

The spec is architecturally sound and demonstrates genuine familiarity with the codebase. The placeholder-plus-job pattern, the three-collection lifecycle mirroring `AsyncMessageDeliveryQueueManager`, and the callback suppression strategy for `AutomaticBotReplyService` are all correct and well-reasoned. However, the spec contains several **internal contradictions** (Persistence-First vs `process_job` pseudocode ordering, double file deletion in CorruptMediaProcessor), a **broken eviction algorithm** that will cause infinite loops under specific conditions, **under-specified `_total_chars` accounting** that will corrupt queue limit enforcement, and a `process_job` **early-return that violates its own Persistence-First principle**. These are not cosmetic — they will cause runtime failures if implemented literally. There are also significant integration gaps around service wiring, recovery ordering, and the poll mechanism.

---

## 2. Design Gaps

### 2.1 `_total_chars` accounting is unspecified when placeholder content changes

**Severity: High — will corrupt queue limits**

`CorrespondentQueue` tracks `_total_chars` to enforce `max_characters`. When a placeholder is created with `content=""` (no caption), `message_size=0`, and `_total_chars` is unchanged. When `update_message_by_media_id` later sets `content` to a transcript of (say) 2000 characters, the spec says "adjusts `message_size`" — but never mentions updating `_total_chars`.

Looking at the code:

```96:105:queue_manager.py
    def _evict_while(self, condition_fn, reason: str, new_message_size: int):
        """
        Helper to evict messages while a condition is true (Item #010).
        Reduces duplication in _enforce_limits.
        """
        while self._messages and condition_fn():
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            self._log_retention_event(evicted_msg, reason, new_message_size)
            logging.info(f"QUEUE EVICT ({self.bot_id}): Message {evicted_msg.id} evicted due to {reason}.")
```

Eviction uses `_total_chars` to decide when to stop. If `_total_chars` is consistently underreported (because placeholder content grew without updating it), the queue will believe it has more headroom than it actually does and will **never evict**, eventually exceeding `max_characters`.

**The spec must specify**: `update_message_by_media_id` must do `self._total_chars -= old_message_size` then `self._total_chars += new_message_size` atomically (within the same synchronous block). A helper like `_update_message_content(msg, new_content)` that handles both `message_size` and `_total_chars` would prevent this from being missed in implementation.

### 2.2 `update_message_by_media_id` is referenced but never fully specified

The spec mentions this method 8+ times across `CorrespondentQueue`, `BotQueuesManager`, `BaseMediaProcessor`, and recovery. It is the **single most critical new method** in the design. Yet its full contract is never defined:

- **Scan algorithm**: Linear scan of the deque? What if the deque has 200 messages? What is the time complexity?
- **Not-found case**: What if the message was evicted by the cleanup job between job completion and delivery? The spec mentions a try/except in section "Update Path," but `process_job` pseudocode doesn't show it.
- **Thread/async safety**: Since `_trigger_callbacks` uses `asyncio.run_coroutine_threadsafe` (line 92 of `queue_manager.py`), and the worker pool presumably runs in the same event loop, there's no thread issue — but the spec should confirm the worker pool runs on the main event loop.
- **Return value**: Should it return a boolean indicating success/failure so callers know whether to proceed with job deletion?

### 2.3 Worker poll mechanism is completely unspecified

The spec says "the `MediaProcessingService` worker pools poll this collection for work" but never defines:

- Poll interval (1 second? 5 seconds? Configurable?)
- Poll query shape (simple `find_one_and_update` with `status: "pending"` and the pool's mime types filter?)
- Backoff when no jobs are found
- How the poll interacts with the asyncio event loop (blocking? async motor queries?)
- Whether there is an `asyncio.Event` or notification mechanism so workers can wake immediately when a new job is inserted

The `AsyncMessageDeliveryQueueManager` uses a 6–12 second random jitter sleep between polls. The media service likely needs a much shorter interval for responsiveness (users expect transcripts in seconds, not 12 seconds + processing time).

### 2.4 `MediaProcessingService` lifecycle is not wired into `main.py`

The spec never states where `MediaProcessingService` is instantiated. Looking at `main.py` lifespan:

```42:116:main.py
async def lifespan(app: FastAPI):
    # ...
    # 2. Initialize AsyncMessageDeliveryQueueManager
    global_state.async_message_delivery_queue_manager = AsyncMessageDeliveryQueueManager(...)
    await global_state.async_message_delivery_queue_manager.move_all_to_holding()
    await global_state.async_message_delivery_queue_manager.start_consumer()
    # ... (no MediaProcessingService anywhere)
```

The spec should specify:
1. `MediaProcessingService` is created during lifespan startup, after MongoDB init but before starting bots.
2. It is stored on `GlobalStateManager` (e.g., `global_state.media_processing_service`).
3. The "move all `media_processing_jobs` → `media_processing_jobs_holding`" sweep runs at this stage.
4. Worker pools are started.
5. On shutdown, worker pools are stopped.
6. `GlobalStateManager` needs a new attribute for this service.

### 2.5 Recovery ordering: `inject_placeholder` vs `_next_message_id` conflict

When a bot starts and reaps jobs from `media_processing_jobs_holding`, it calls `inject_placeholder(message)` which "uses the ID from the provided Message" (i.e., the ID from the previous session). But `CorrespondentQueue.initialize()` loads `_next_message_id` from MongoDB:

```68:82:queue_manager.py
    async def _initialize_next_message_id(self):
        last_message = await self._queues_collection.find_one(
            {"bot_id": self.bot_id, "provider_name": self.provider_name, "correspondent_id": self.correspondent_id},
            sort=[("id", DESCENDING)]
        )
        if last_message and 'id' in last_message:
            self._next_message_id = last_message['id'] + 1
```

If placeholder message IDs (from the previous session) are higher than the last persisted ID, and then `inject_placeholder` inserts them, subsequent calls to `add_message` could generate IDs that collide with placeholder IDs (because `_next_message_id` was set from the DB, which doesn't contain unpersisted placeholders). The spec should specify that after all placeholders are injected, `_next_message_id` is adjusted to `max(current_next_id, max(placeholder_ids) + 1)`.

### 2.6 Node.js config source for `media_storage_quota_gb`

The spec uses `botConfig?.media_storage_quota_gb` in `server.js`, but the Node.js server receives config only via `POST /initialize` (`config` field from Python). There is no MongoDB access from Node. The spec should state whether this value is:
- Passed from Python in the initialize payload (requires extending `ChatProviderSettings` in `config_models.py`)
- A global constant in `server.js`
- Read from a shared config document

Given the codebase pattern, passing it in the initialize payload is the cleanest option.

### 2.7 Sticker vs image/webp mime type ambiguity

Both "Image pool" (`image/webp`) and "Sticker pool" (`image/webp`) map to the same mime type. The processor routing table would match the first pool that claims `image/webp`, making the second unreachable. WhatsApp distinguishes stickers from images by message type (`stickerMessage` vs `imageMessage`), not by mime type. The spec should either:
- Have Node.js send a synthetic mime type for stickers (e.g., `sticker/webp`)
- Use the message type as a routing key alongside mime type
- Merge sticker and image pools

### 2.8 Cleanup job access to GlobalStateManager

The cleanup job needs to iterate all `BotQueuesManager` instances (to scan for stale placeholders) AND query MongoDB (for stale jobs). The spec doesn't specify how the cleanup job gets these references. In the current architecture, scheduled jobs on APScheduler receive no arguments beyond what's bound at registration time. The cleanup function would need a closure over `global_state` or be a method on a service with access to it.

### 2.9 No specification of `BotQueuesManager` changes for job submission

The spec extends `BotQueuesManager.add_message()` with media params but doesn't show the implementation of the job submission logic. Specifically:
- `add_message` needs a reference to the `media_processing_jobs` MongoDB collection to write job records. Currently `BotQueuesManager` only has a reference to `queues_collection` (for message ID initialization). How does it get `media_processing_jobs`?
- Error handling: if the MongoDB job insert fails after the placeholder is already in the deque, the placeholder becomes orphaned.

### 2.10 `inject_placeholder` should fire callbacks for `completed` jobs during recovery

The spec says `inject_placeholder` does NOT fire `_trigger_callbacks`. Then for `completed` jobs, the bot calls `update_message_by_media_id`, which DOES fire callbacks. This is correct. But the ordering matters: all placeholders must be injected first (for all correspondents), and only then should completed jobs trigger `update_message_by_media_id`. If a completed job's callback triggers `AutomaticBotReplyService` which calls `sendMessage`, the provider must be connected. The spec should specify that recovery happens after `provider.start_listening()` but before (or just after) the status callback fires `on_bot_connected`.

---

## 3. Design Errors

### 3.1 `process_job` pseudocode contradicts the Persistence-First principle

**Severity: High — data loss on crash**

The spec's section "Update Path After Processing" (step 5) says:

> Every result is saved to the Job Document (status set to "completed") **before** attempting in-memory queue updates.

But the `process_job` pseudocode does the opposite:

```python
# From the spec's BaseMediaProcessor.process_job:
result = await self.process_media(file_path, mime_type, caption)

# IN-MEMORY UPDATE FIRST
await bot_queues.update_message_by_media_id(correspondent_id, guid, result.content)

# DB PERSISTENCE SECOND
if result.failed_reason:
    await self._move_to_failed(job, db, error=result.failed_reason)
else:
    await self._remove_job(job, db)
```

If the process crashes after the in-memory update but before the DB write, the placeholder is gone from the queue but the job is still `"processing"` in MongoDB. On restart, the job would be re-processed (moved to holding, then re-claimed), but there would be no placeholder to update (it was replaced and then lost in the crash). The worker would then hit the "message not found in deque" case.

**Fix**: The pseudocode should persist `status="completed"` + `result=transcript` to MongoDB first (trying active then holding collections), and THEN update the in-memory queue. This matches the prose but not the code.

### 3.2 `process_job` early-return when bot is missing violates Persistence-First

```python
# From the spec's BaseMediaProcessor.process_job:
bot_queues = all_bot_queues.get(bot_id)
if not bot_queues:
    logging.warning(f"BotQueuesManager not found for bot_id={bot_id}. Job left for cleanup.")
    return  # <-- Returns without processing or persisting
```

If the bot stops between job claiming (`status="processing"`) and the worker starting `process_job`, the worker finds no `BotQueuesManager` and returns. The job stays in `"processing"` state in `media_processing_jobs_holding` (it was moved there when the bot stopped). No worker will ever claim it again (it's not `"pending"`). The cleanup job catches it after 3 hours, but that's a long delay for what could be a quick fix.

**Fix**: If the bot is gone at the start of `process_job`, the worker should still process the media, persist the result (`status="completed"` in the holding collection), and let the bot reap it on next startup. The early-return should only happen if the file doesn't exist (nothing to process).

### 3.3 `_evict_while` rewrite will cause infinite loops

**Severity: Critical — will hang the event loop**

The spec says to rewrite eviction to "scan from left to right, skip messages with `media_processing_id`, find the oldest unprotected message, remove it." But the current `_evict_while` is a `while condition():` loop. Consider this scenario:

- Queue has 5 messages: `[placeholder, placeholder, msg_A, msg_B, msg_C]`
- `max_messages = 4`, a new message arrives
- `_enforce_limits` calls `_evict_while(lambda: len(self._messages) >= self.max_messages, ...)`
- Iteration 1: scan from left, skip placeholder at 0, skip placeholder at 1, find `msg_A` at 2, delete it. Queue: `[placeholder, placeholder, msg_B, msg_C]` — 4 messages, still `>= max_messages`
- Iteration 2: scan from left, skip 0, skip 1, find `msg_B` at 2, delete it. Queue: `[placeholder, placeholder, msg_C]` — 3 messages, condition is False, stop.
- New message added: `[placeholder, placeholder, msg_C, new_msg]` — 4 messages

That works. But consider the degenerate case:

- Queue has 5 messages, ALL are placeholders: `[p1, p2, p3, p4, p5]`
- New message arrives, `_enforce_limits` runs
- `_evict_while(lambda: len(self._messages) >= 5, ...)`: scan from left, all are protected, no eligible message found
- **The while loop's condition is still True (5 >= 5), but no message was evicted. Infinite loop.**

The spec acknowledges this could "allow the queue to grow infinitely" but the fix as described (scanning for an eligible message) doesn't address the loop termination condition. The inner scan must signal "no eligible message found" to break the outer while loop. The spec's description says "the loop must scan" but doesn't handle the "all protected" terminal case.

**Fix**: The eviction helper must return a boolean indicating whether an eviction occurred. If it returns `False` (no eligible message), the while loop breaks regardless of the condition.

### 3.4 Double file deletion in CorruptMediaProcessor

The spec describes `CorruptMediaProcessor` step 1 as "Deletes the media file from the shared volume (if one exists)." Then `BaseMediaProcessor.process_job` always calls `self._delete_media_file(file_path)` at the end. Both paths delete the same file.

For `CorruptMediaProcessor`, no file may exist on disk (Node.js already deleted the partial file after 3 failed attempts). So the base class's deletion is a no-op (file doesn't exist). But if the corrupt processor somehow received a file (e.g., partial write), both would try to delete it — first the subclass in `process_media`, then the base class. The second `unlink` would raise `FileNotFoundError` unless guarded.

**Fix**: Clarify that file deletion is exclusively the responsibility of `BaseMediaProcessor.process_job` (i.e., the base class). Subclasses should never delete files — they only produce `ProcessingResult`. Remove step 1 from `CorruptMediaProcessor`.

### 3.5 Age-based eviction condition breaks with placeholders at index 0

The current eviction checks the oldest message's age:

```112:115:queue_manager.py
        self._evict_while(
            lambda: (now - self._messages[0].accepted_time / 1000) > self.max_age_seconds,
            "age", new_message_size
        )
```

When the eviction is rewritten to skip placeholders, the condition `self._messages[0].accepted_time` would reference a placeholder. If the placeholder is old (which it likely is — it's been waiting for processing), the condition evaluates to `True`, the scan finds no eligible message at index 0 (it's protected), finds one at index N, and evicts it. But the condition still checks index 0's age, not the newly-evicted message's age. On the next iteration, the same old placeholder at index 0 makes the condition True again, evicting the next unprotected message. This continues until all unprotected messages are evicted, even if they're well within the age limit.

**Fix**: Age-based eviction should check the age of the message actually being considered for eviction, not always index 0. The condition function approach needs to be rethought — likely the condition and the scan should be merged into a single loop: "find the oldest unprotected message; if it violates the age limit, evict it; otherwise stop."

---

## 4. Possible Enhancements

### 4.1 Per-file size limit

The spec enforces a global disk quota but no per-file limit. A single 500MB video could consume a large portion of the quota. Consider a configurable per-file size limit (e.g., 25MB) checked in Node.js before streaming. WhatsApp has its own limits (~16MB for media, ~100MB for documents), so this is mainly a safety net.

### 4.2 Media content formatting for AI context

The spec says final content is "Caption + appended transcript/description" but doesn't define the format. For `AutomaticBotReplyService`, the AI needs to understand what it's receiving. Consider a structured format:

```
[Image received] A photo showing a sunset over the ocean with orange and pink clouds.
Caption: "Beautiful evening!"
```

vs just:

```
Beautiful evening! A photo showing a sunset over the ocean with orange and pink clouds.
```

The first gives the AI clear context about what was sent. This formatting choice affects AI response quality and should be standardized across all processors.

### 4.3 Retry mechanism for transient API failures

The spec explicitly states "single attempt, no retries" for media processing. External API calls (OpenAI, Gemini) can fail transiently (rate limits, timeouts, network blips). A single-retry-with-backoff before moving to `_failed` would significantly improve reliability. The `asyncio.wait_for` timeout already handles hangs; adding one retry for non-timeout errors is low-risk and high-value.

### 4.4 Expose pending media count in bot status API

When a bot has many pending media messages, the user should see this in the UI. The status API (`get_status`) could include a `pending_media_jobs` count by querying `media_processing_jobs` for the bot's `bot_id`.

### 4.5 Startup script media volume cleanup

The `start.sh` script should optionally clear `media_store/pending_media/` on startup (or at least warn about leftover files). Stale files from a previous crash would count toward the quota and confuse GUID lookups. The spec's app-level startup sweep moves jobs to holding but doesn't clean orphaned files (files with no matching job record).

### 4.6 Configuration validation for processor definitions

The spec loads processor pool definitions from MongoDB (`_mediaProcessorDefinitions`). There's no validation specified for:
- Duplicate mime types across pools (would cause non-deterministic routing)
- Missing catch-all pool (`mimeTypes: []`)
- Invalid `processorClass` names (typos)
- Zero or negative `concurrentProcessingPoolSize`

A startup validation step that rejects invalid configurations would prevent silent failures.

### 4.7 `pop_ready_message` could return count of skipped placeholders

When `pop_ready_message` scans and finds only placeholders, it returns `None`. The caller (IngestionService) has no way to distinguish "queue is empty" from "queue has only placeholders." Returning a tuple `(message, skipped_count)` or logging the skip count would aid debugging.

---

## 5. Risky Changes

### 5.1 `IngestionService.stop()` final drain — behavioral change

The current `stop()` sets the event and awaits the task:

```75:80:services/ingestion_service.py
    async def stop(self):
        if self._task:
            self._stop_event.set()
            await self._task
            self._task = None
```

Adding a final drain pass means `stop()` will now iterate all queues and pop remaining ready messages after the background task exits. This is correct, but it changes the timing of the last DB writes — they now happen during shutdown, potentially under time pressure. If MongoDB is slow or unreachable during shutdown, `stop()` could hang. Consider wrapping the final drain in `asyncio.wait_for` with a timeout.

### 5.2 Eviction rewrite touches core queue contract

`_evict_while` is called on every `add_message`. The rewrite to `_evict_eligible` changes the fundamental eviction guarantee from "oldest messages are evicted first" to "oldest non-placeholder messages are evicted first." This is correct for media support but is a high-risk change because:
- Every incoming message exercises this code path
- Bugs manifest as silent data corruption (wrong messages evicted or queue limits exceeded)
- The degenerate case (all messages are placeholders) must be explicitly handled

Recommend: implement with extensive unit tests covering all edge cases before integration testing.

### 5.3 `Message` dataclass change propagates everywhere

Adding `media_processing_id: Optional[str] = None` to `Message`:

```28:38:queue_manager.py
@dataclass
class Message:
    id: int
    content: str
    sender: Sender
    source: str
    accepted_time: int = field(default_factory=lambda: int(time.time() * 1000))
    message_size: int = 0
    originating_time: Optional[int] = None
    group: Optional[Group] = None
    provider_message_id: Optional[str] = None
```

`asdict(message)` is used by `IngestionService` to create MongoDB documents. The new field will appear in all ingested documents (as `null` for non-media messages). This is harmless but changes the document schema. More importantly, any code that constructs a `Message` from a dict (e.g., deserialization from `placeholder_message` in job records) must handle the new field. Since `Message` is a `@dataclass` (not Pydantic), construction is positional or keyword — keyword is safer for optional fields.

### 5.4 Shared volume permission model is Linux-specific

The spec's UID/GID pattern (`user: "${CURRENT_UID}:${CURRENT_GID}"`) and `start.sh` using `id -u`/`id -g` work correctly on Linux. On macOS with Docker Desktop, named volumes are transparently handled by the VM layer and UID/GID mismatches rarely cause issues. On Windows with WSL2 (which is relevant — the workspace path is `c:\tufin\code\...`), the behavior depends on the WSL distribution and Docker backend. This should be documented as a Linux-first design with known limitations on other platforms.

### 5.5 Concurrent queue modifications during `update_message_by_media_id`

The media worker calls `update_message_by_media_id` which scans the deque and modifies a message in-place. Simultaneously, `add_message` could be appending to the deque, and `pop_ready_message` (from IngestionService) could be scanning and removing from it. In CPython, the GIL prevents true concurrent access, but async coroutines interleave at `await` points. Since `update_message_by_media_id` is sync (no awaits during the scan/update), and `add_message` is async but the deque mutation part is sync, there's no interleaving risk. However, if `update_message_by_media_id` ever becomes async (e.g., to await a callback), interleaving becomes possible. The spec should note that the deque scan and mutation must be atomic (no awaits between finding the message and updating it).

### 5.6 `inject_placeholder` bypasses all queue limits

During recovery, `inject_placeholder` inserts messages without checking `max_messages`, `max_characters`, or `max_days`. If a bot had 50 pending media jobs when it crashed, injecting 50 placeholders at startup could push the queue far beyond its configured limits. Subsequent `add_message` calls would then aggressively evict non-placeholder messages to compensate, potentially losing recent messages.

Consider: either enforce limits during `inject_placeholder` (evicting only non-placeholders if needed) or accept the temporary over-limit state and let normal eviction correct it as messages arrive.

---

## 6. Subtle Issues and Edge Cases

### 6.1 Caption-only media messages may confuse the AI

When a media message has a caption but processing takes 60 seconds, the placeholder sits in the queue with `content=caption` and `media_processing_id=set`. The spec says `_trigger_callbacks` is NOT fired for placeholders. So the AI never sees the caption alone — it waits for the full content. This is correct. But if a **text message** arrives after the media message, the AI processes it immediately (the placeholder is skipped by the ingester but the text message triggers callbacks). The AI's conversation history now has the text response without the media context. When the media processing completes and the placeholder is finalized, the callback fires and the AI sees the transcript — but the conversation history now shows: `text_message → ai_response → transcript`. The AI responds to the transcript out of context.

This is the "accepted trade-off" mentioned in the spec, but it has a worse UX impact than just ordering — it can cause the AI to give a confused response to the transcript because it already responded to subsequent messages.

### 6.2 `pop_ready_message` changes message consumption ordering in the DB

The spec acknowledges "DB insertion order may not match receive order." But this has a downstream impact: any feature that queries the `queues` collection (e.g., for historical context or reporting) and sorts by `_id` or insertion order will see messages out of receive order. Queries should use `originating_time` or `accepted_time` for correct ordering. The spec should call this out for implementers of future features.

### 6.3 Race between cleanup job and worker delivery

The cleanup job runs every hour and removes placeholders older than 3 hours. A worker processing a slow video (say, 2 hours 55 minutes) could complete processing just as the cleanup job runs. The cleanup job removes the placeholder and dead-letters the job. The worker then tries to update the queue (placeholder gone) and the job (moved to failed). The spec handles this in step 6 (the "Late-Returning Hero") where the worker logs a warning and exits. But the user's message is effectively lost — it was a valid transcription that arrived just too late. Consider making the cleanup threshold higher than the maximum expected processing time (e.g., 6 hours instead of 3), or skipping cleanup for jobs in `"processing"` state.

### 6.4 Memory implications of stub processors for Phase 1 testing

The stub video processor sleeps for 60 seconds. During those 60 seconds, the worker is occupied and the asyncio event loop is blocked (unless `asyncio.sleep` is used instead of `time.sleep`). The spec mentions stubs "sleep for the configured duration" but doesn't specify `asyncio.sleep`. If `time.sleep` is used, it blocks the event loop for 60 seconds, freezing all other coroutines. Ensure stubs use `await asyncio.sleep()`.

---

## 7. Comparison with Existing Codebase Patterns

### 7.1 Three-collection pattern alignment

The spec mirrors `AsyncMessageDeliveryQueueManager`'s pattern well:

| Aspect | Delivery Queue | Media Processing Jobs |
|---|---|---|
| Active collection | `async_message_delivery_queue_active` | `media_processing_jobs` |
| Holding collection | `async_message_delivery_queue_holding` | `media_processing_jobs_holding` |
| Failed collection | `async_message_delivery_queue_failed` | `media_processing_jobs_failed` |
| App startup sweep | `move_all_to_holding()` | All active → holding + reset `processing` → `pending` |
| Bot connect | `move_bot_to_active(bot_id)` | Reap from holding, inject placeholders, move back |
| Bot disconnect | `move_bot_to_holding(bot_id)` | Move active → holding |
| Consumer | `_consumer_loop` (random sample) | Per-pool worker poll |
| Retry | 3 attempts, then failed | Single attempt, then failed |

The key difference is that the delivery queue's consumer uses `$sample` for random selection, while the media service uses `find_one_and_update` for atomic claiming. The media approach is better for fairness (round-robin per pool) and prevents double-claiming.

### 7.2 Callback mechanism alignment

The callback chain works as:

```
CorrespondentQueue._trigger_callbacks(message)
  → asyncio.run_coroutine_threadsafe(callback(...), self.main_loop)
    → BotQueuesManager callback wrapper
      → SessionManager._on_queue_message(user_id, correspondent_id, message)
        → (filters out bot/user_outgoing)
          → AutomaticBotReplyService.handle_message(correspondent_id, message)
```

The spec's plan to suppress callbacks for placeholders by checking `media_processing_id` at the `CorrespondentQueue.add_message` level is correct. The `update_message_by_media_id` callback will follow the same chain. One concern: `_on_queue_message` filters `source == 'bot'` and `source == 'user_outgoing'`. Media messages have source `'user'` (they're incoming), so they pass through. The spec doesn't change `source` handling, which is correct.

---

## 8. Recommended Implementation Order

Based on dependency analysis:

1. **Message dataclass** — add `media_processing_id` field
2. **CorrespondentQueue** — `_evict_eligible`, `pop_ready_message`, `inject_placeholder`, `update_message_by_media_id`, callback suppression
3. **BotQueuesManager** — extend `add_message` with media params, add job submission
4. **IngestionService** — switch to `pop_ready_message`, add final drain
5. **MongoDB collections and indexes** — `media_processing_jobs` / `_holding` / `_failed`
6. **MediaProcessingService** — worker pool infrastructure, poll loop
7. **BaseMediaProcessor + stub processors** — process_job lifecycle, Phase 1 stubs
8. **server.js** — media download, quota check, metadata forwarding
9. **WhatsAppBaileysProvider** — handle media metadata in `_process_messages`
10. **BotLifecycleService** — media job lifecycle (move to holding/active, recovery reaping)
11. **main.py lifespan** — MediaProcessingService startup/shutdown
12. **Cleanup job** — scheduled stale placeholder/job cleanup
13. **docker-compose.yml** — shared volume, UID/GID
14. **Integration testing** — end-to-end with stub processors

---

## 9. Summary Table

| Category | Count | Severity |
|---|---|---|
| **Design gaps** | 10 | 3 high, 4 medium, 3 low |
| **Design errors** | 5 | 2 critical (infinite loop, persistence ordering), 3 high |
| **Enhancements** | 7 | All medium priority |
| **Risky changes** | 6 | 2 high (eviction, Message propagation), 4 medium |
| **Subtle issues** | 4 | 2 medium (AI context, race), 2 low |

### Critical items to resolve before implementation:

1. **Fix `_evict_while` rewrite** — the spec's description will cause infinite loops when all messages are placeholders. The loop must break when no eligible message is found, and age-based eviction must check the candidate's age, not index 0.
2. **Fix `process_job` ordering** — persist result to MongoDB BEFORE in-memory queue update (match the prose, not the pseudocode).
3. **Fix `process_job` early-return** — if bot is missing, still process the media and persist the result rather than abandoning the job.
4. **Specify `_total_chars` accounting** — `update_message_by_media_id` must update `_total_chars` alongside `message_size`.
5. **Fully specify `update_message_by_media_id`** — this is the most critical new method and needs a complete contract.
