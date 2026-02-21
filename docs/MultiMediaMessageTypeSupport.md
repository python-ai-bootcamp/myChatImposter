# Multimedia Message Type Support

## Problem Statement

When media messages (video, audio, image) arrive, converting them to text can take up to a minute. Holding the bot's message pipeline while processing would:
- Block all subsequent messages for that correspondent
- Explode memory if multiple heavy files arrive simultaneously

## Design Overview

Messages flow from any Chat Provider → `BotQueuesManager` → `CorrespondentQueue`. The solution adds a non-blocking processing layer at the `BotQueuesManager` level, keeping it **provider-agnostic** ("one implementation, fits all providers").

---

## Message Schema Change

Add `media_processing_id: Optional[str]` to the `Message` dataclass (alongside existing fields: `id`, `content`, `sender`, `source`, `accepted_time`, `message_size`, `originating_time`, `group`, `provider_message_id`).

| Field | Value during processing | Value when done |
|---|---|---|
| `content` | Caption text if provided, otherwise `""` | Caption + appended transcript/description |
| `media_processing_id` | GUID (e.g. `"a3f2-..."`) | `None` (removed) |
| `message_size` | `len(caption)` or `0` | `len(final content)` |

---

## Shared Media Volume

A shared Docker volume (`media_staging`) is mounted into both the Baileys Node.js server and the Python backend at `media_store/pending_media/`. This allows the Node.js server to stream media files directly to disk, and the Python backend to read and delete them — **zero media bytes are exchanged between containers over the network**.

```yaml
# docker-compose.yml
services:
  whatsapp_baileys_server:
    volumes:
      - media_staging:/app/media_store/pending_media

  backend:
    volumes:
      - media_staging:/app/media_store/pending_media

volumes:
  media_staging:
```

---

## Flow for a Media Message

1. **Node.js receives media** → generates a GUID, streams the media to disk at `media_store/pending_media/<guid>` using Baileys' streaming API (`downloadMediaMessage(msg, 'stream')`). Media bytes never fully load into Node.js memory.
2. **Node.js sends metadata to Python** via WebSocket — only the GUID, mime type, caption, and original filename. No media bytes cross the wire.
3. **Python provider receives metadata** → calls `BotQueuesManager.add_message()` with the media params (GUID, mime type, caption, filename).
4. **Placeholder insertion**: `BotQueuesManager` verifies the media file exists on the shared volume, then adds a `Message` to the `CorrespondentQueue` with `content=<caption>` (or `""`) and `media_processing_id=<guid>`.
5. **Non-blocking processing trigger**: A job record is written to the **`media_processing_jobs`** MongoDB collection. This IS the job submission — the `MediaProcessingService` worker pools poll this collection for work. Each job record contains:
   - `placeholder_message` — the full serialized `Message` placeholder dict (all fields including `bot_id`, `correspondent_id`, `media_processing_id`, etc.)
   - `guid` — used to locate the raw media file at `media_store/pending_media/<guid>`
   - `original_filename` *(optional)* — provided by the provider if available; used to assist processing (e.g. file extension hints)
   - `mime_type` — determines which processing path to use (transcription vs. vision)
6. **Processing completes**: The worker calls `BotQueuesManager.update_message_by_media_id(correspondent_id, guid, transcript)`. Using the `correspondent_id` from the job metadata, it goes directly to the correct `CorrespondentQueue` and updates its `content` and `message_size`, then fires `_trigger_callbacks`. The job record is then **deleted from `media_processing_jobs`** and the raw media file is **deleted from disk**.

---

## Provider Interface for Media Messages

The existing `add_message()` method on `BotQueuesManager` is extended with optional media parameters:

```python
async def add_message(
    self,
    content: str,                          # if a regular text message, will contain the text. If a media message, will contain the caption text if provided, or empty string if no caption is provided
    sender: Sender,
    source: str,
    originating_time: Optional[int] = None,
    group: Optional[Group] = None,
    provider_message_id: Optional[str] = None,
    # --- New optional media params ---
    media_processing_id: Optional[str] = None,  # GUID — file already on shared volume
    mime_type: Optional[str] = None,
    original_filename: Optional[str] = None
)
```

If `media_processing_id` and `mime_type` are provided, the media pipeline kicks in (placeholder → job). If not, the message is treated as plain text. This is the **single entry point** for all providers — the provider's job ends after calling this method.

### Required Change in `server.js` (Baileys Node.js Server)

The current `processMessage` function discards media and captions:

```javascript
// CURRENT — media is lost, caption is lost
let messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text;
if (!messageContent) {
    messageContent = `[User sent a non-text message: ${type}]`;
}
```

This must be updated to detect media types, extract the caption, stream the media to the shared volume, and return only metadata:

```javascript
// NEW — stream media to shared volume, return only metadata
const mediaTypes = {
    imageMessage:  { caption: msg.message.imageMessage?.caption },
    videoMessage:  { caption: msg.message.videoMessage?.caption },
    audioMessage:  { caption: null },  // audio has no caption
};

const mediaInfo = mediaTypes[messageType];  // messageType already resolved above (line 387)

if (mediaInfo !== undefined) {
    const guid = crypto.randomUUID();
    const mimetype = msg.message[messageType]?.mimetype;
    const filename = msg.message[messageType]?.fileName || null;
    const caption = mediaInfo.caption || '';

    // Stream media directly to shared volume — never fully loaded into memory
    const stream = await downloadMediaMessage(msg, 'stream', {});
    const writePath = path.join('/app/media_store/pending_media', guid);
    const writeStream = fs.createWriteStream(writePath);
    await new Promise((resolve, reject) => {
        stream.pipe(writeStream);
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
    });

    // Return only metadata — no bytes cross the wire to Python
    return {
        ...existingFields,
        message: caption,
        media_processing_id: guid,
        mime_type: mimetype,
        original_filename: filename,
    };
}
```

The Python `whatsAppBaileys.py` provider passes the metadata (GUID, mime type, filename) to `add_message()`. No bytes are decoded or transferred.

## MediaProcessingService (Background Worker Pool)

A fixed-concurrency pool to avoid memory bloat and starvation across bots. Only invoked for non-text media — the routing decision is made by `BotQueuesManager` before submission. Text messages bypass this service entirely and go straight to the queue.

- **Audio** → speech-to-text API → transcript
- **Video** → vision/transcription API → description or transcript
- **Image** → vision API → text description

### Unsupported Mime Type Handling

If `BotQueuesManager` receives a mime type that does not match any pool definition in `_mediaProcessorDefinitions`, it **fails immediately at the routing point** — before inserting a placeholder into the queue:

1. The media file is deleted from the shared volume.
2. A record is written directly to `media_processing_jobs_failed` with `error: "unsupported mime type: <mime_type> — no processing pool defined"`.
3. A warning is logged so the operator knows to update `_mediaProcessorDefinitions`.
4. **If the message has a caption**: the `media_processing_id`, `mime_type`, and `original_filename` fields are stripped, and the message is **also** added to the `CorrespondentQueue` as a **regular text message** with the caption as its `content`. The `media_processing_jobs_failed` record exists in parallel for investigation.
5. **If no caption**: no message is added to the queue. The `media_processing_jobs_failed` record is the only trace.

**Fail fast at the door — do not let unsupported types enter the pipeline, but never lose a caption.**

### Concurrency Configuration

Pool definitions are loaded from the `bot_configurations` MongoDB collection, document `_id: "_mediaProcessorDefinitions"`. The document contains an array:

```json
[
  { "mimeTypes": ["audio/ogg", "audio/mpeg"], "concurrentProcessingPoolSize": 2 },
  { "mimeTypes": ["video/mp4", "video/webm"], "concurrentProcessingPoolSize": 1 },
  { "mimeTypes": ["image/jpeg", "image/png", "image/webp"], "concurrentProcessingPoolSize": 3 }
]
```

On startup, `MediaProcessingService` creates one worker pool per array entry, sized to `concurrentProcessingPoolSize`, handling only the listed mime types. Round-robin is applied **per pool** across bots to prevent starvation.

### Memory Behavior During Processing

- **Audio**: Streamed from disk using a file handle (`open(file, 'rb')`). `httpx` uploads in chunks — the full audio is never loaded into Python heap. Genuinely low-memory.
- **Video**: Gemini's File API accepts a streaming upload (disk → network), returning a URI used for subsequent LLM calls — low-memory.
- **Image**: Base64-encoded before sending to vision APIs (full image bytes in memory). Acceptable given typical image sizes.

---

## Cleanup Job

A background job runs every **1 hour**. It scans all `CorrespondentQueue` instances for messages where `media_processing_id` is set and the message has been alive for more than **3 hours**.

For each stale placeholder found:
1. **Remove** the placeholder message from the `CorrespondentQueue`.
2. **Locate the matching job** and move it to `media_processing_jobs_failed`:
   - Found in `media_processing_jobs` → move and set `error`: `"message was transferred from media_processing_jobs to media_processing_jobs_failed by cleanup job"`
   - Found in `media_processing_jobs_holding` → move and set `error`: `"message was transferred from media_processing_jobs_holding to media_processing_jobs_failed by cleanup job"`
   - Found in neither → create a new record in `media_processing_jobs_failed` with `error`: `"message was missing and created from scratch in media_processing_jobs_failed by cleanup job"`

**Additionally**, the cleanup job directly queries `media_processing_jobs_holding` for any job records older than **3 hours** — regardless of whether an in-memory queue placeholder exists. This catches stale jobs for bots that are currently **disconnected** (their in-memory queues are not active, so the queue scan above would never find them). For each such record found:
- Move it to `media_processing_jobs_failed` with `error`: `"job in holding exceeded 3-hour threshold and was moved to media_processing_jobs_failed by cleanup job"`
- Delete the raw media file from disk.

---

## Job Collection Lifecycle

Three MongoDB collections manage job state, mirroring the `async_message_delivery_queue_manager` pattern:

| Collection | Purpose |
|---|---|
| `media_processing_jobs` | Active jobs — bot is running and jobs are being processed |
| `media_processing_jobs_holding` | Holding jobs — bot is stopped, jobs are paused |
| `media_processing_jobs_failed` | Failed jobs — processing failed on single attempt |

### Lifecycle Transitions
- **App startup (init phase)**: All records in `media_processing_jobs` are moved to `media_processing_jobs_holding`. No bot is running yet.
- **Bot starts**: All holding jobs for that `bot_id` are moved from `media_processing_jobs_holding` → `media_processing_jobs`. The `placeholder_message` from each job is re-injected into the correct `CorrespondentQueue` and processing resumes.
- **Bot stops**: All active jobs for that `bot_id` are moved from `media_processing_jobs` → `media_processing_jobs_holding`.
  > **Note on in-flight jobs**: If a job is currently being processed at the moment the bot stops, the worker will attempt to call `update_message_by_media_id` on a `CorrespondentQueue` that no longer exists. This call is wrapped in a try/except — the error is logged and the job is left to be handled by the cleanup job.
- **Processing fails** (single attempt, no retries): Job is moved immediately to `media_processing_jobs_failed` for inspection with an added `error` property containing a text message describing the fail reason, and the raw media file is deleted from disk. No retries — each attempt consumes expensive tokens and resources, we don't want to retry error-prone messages.

> [!IMPORTANT]
> **Required fix — `IngestionService` final drain pass on bot stop**
> Currently `IngestionService.stop()` sets the stop event and exits immediately — if the ingester is in its 1-second sleep, it wakes up, sees the stop flag, and exits without draining remaining messages. Any messages that arrived since the last ingestion cycle are lost.
>
> **Fix**: After the background task finishes, run one final drain pass (`_drain_once()`) before returning from `stop()`.

---

## AutomaticBotReply Behavior

The `AutomaticBotReplyService` builds its AI context from an **in-memory LangChain `ChatMessageHistory`** object — it does **not** read from the `CorrespondentQueue`. It is driven purely by callbacks fired by `_trigger_callbacks`.

Therefore, the correct integration point is the **callback trigger**, not context filtering:

- When a **placeholder message** is added (`media_processing_id` is set, `content` is empty): `_trigger_callbacks` is **NOT fired**. The AI is never notified.
- When **processing completes** and `update_message_by_media_id` clears the `media_processing_id` and sets `content`: `_trigger_callbacks` **IS fired**. The AI receives the finalized text content and responds normally.

This requires zero changes to `AutomaticBotReplyService` itself. The suppression is a single conditional at the end of the shared `CorrespondentQueue.add_message()`:

```python
# Only trigger callbacks for fully ready messages
if not message.media_processing_id:
    self._trigger_callbacks(message)
```

And `update_message_by_media_id` fires `_trigger_callbacks` after setting `content` and clearing `media_processing_id`.

---

## Update Path After Processing

1. `BotQueuesManager.update_message_by_media_id(correspondent_id, guid, transcript)` — uses `correspondent_id` to go directly to the correct `CorrespondentQueue`, then searches its deque for the message by `guid`.
2. Updates `content`, `message_size`, clears `media_processing_id`, adjusts `_total_chars`, fires callbacks.
3. **The media processor never touches the database directly.**

---

## Ingestion Coordination: Skip-Pop Approach

The `IngestionService` **skips** (does not pop) any message where `media_processing_id` is not `None`. The message stays in the deque until processing completes and clears the field. On the next ingestion cycle, the message is "ready" and is popped and persisted normally — fully processed, in one clean `insert_one`.

**Benefits:**
- No locks, no coordination between services.
- The media processor only ever reads/writes in-memory state.
- The ingester only ever persists complete, processed messages.
- No DB `update_one` ever needed for media processing.

**Known side effect:** Messages that arrive after a media placeholder will be persisted first. DB insertion order may not match receive order, but queries by `id` or `originating_time` preserve the correct sequence.

**Known limitation — message ordering is not guaranteed for media:** Since different mime types have separate pools and round-robin is applied per pool, the order in which transcripts arrive is non-deterministic. For example, if a user sends a video followed by a text message, the AI may respond to the text before the transcript is ready. This is an accepted and understood trade-off of the async processing design — not a bug to fix.

---

## Crash / Startup Recovery

Because the full placeholder `Message` is stored in the `media_processing_jobs_holding` collection (all jobs are moved there on startup init), recovery is straightforward:

1. On startup, all records in `media_processing_jobs` are moved to `media_processing_jobs_holding`.
2. As each bot connects, its jobs are moved to `media_processing_jobs` and the `MediaProcessingService` picks them up.
3. For each job, it deserializes the `placeholder_message` and re-injects it into the correct `CorrespondentQueue`.
4. It then resumes processing the media file from disk and updates the queue as normal when done.
5. The job record is deleted and the media file is removed from disk once processing completes successfully.

**MongoDB is the source of truth for crash recovery — no data is lost.**

---

## Placeholder Processors (Phase 1 — Testing Only)

Before integrating real speech-to-text or vision APIs, each media type pool will have a **stub processor** that simulates the full pipeline without performing actual media analysis. This allows end-to-end testing of all infrastructure (queues, job lifecycle, skip-pop ingestion, callback triggers, DB collections) with zero API cost.

Each stub processor:
1. Opens a file handle to the media file at `media_store/pending_media/<guid>` (simulating real access).
2. Sleeps for the configured duration (simulating processing time).
3. Deletes the media file from disk.
4. Returns a fixed text string as if it were a real transcript/description.

### Stub Implementations

| Media Type | Sleep | Returned Text |
|---|---|---|
| Image | 5 seconds  | `[Transcripted image multimedia message with guid='<guid>']` |
| Audio | 10 seconds | `[Transcripted audio multimedia message with guid='<guid>']` |
| Video | 60 seconds | `[Transcripted video multimedia message with guid='<guid>']` |

> **Note**: These stubs will be replaced with real API-backed processors in a future phase. The stub and real implementations share the same interface — the pool configuration drives which processor class is used per mime type.
