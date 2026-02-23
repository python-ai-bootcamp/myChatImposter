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

## Shared Media Volume & Storage Quota

A shared Docker volume (`media_staging`) is mounted into both the Baileys Node.js server and the Python backend at `media_store/pending_media/`. This allows the Node.js server to stream media files directly to disk, and the Python backend to read and delete them — **zero media bytes are exchanged between containers over the network**.

To prevent media downloads from exhausting the host's primary disk, an application-level quota is enforced. The limit is defined by the `media_storage_quota_gb` property in the configuration collection.

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
4. **Placeholder insertion**: `BotQueuesManager` adds a `Message` to the `CorrespondentQueue` with `content=<caption>` (or `""`) and `media_processing_id=<guid>`. No file validation is performed — if the file is missing or corrupt, the processor handles the implications.
5. **Non-blocking processing trigger**: `BotQueuesManager.add_message()` writes a job record to the **`media_processing_jobs`** MongoDB collection. This IS the job submission — the `MediaProcessingService` worker pools (each one consumed by their dedicated mediaProcessor for mimetype) poll this collection for work. Each job record contains:
   - `bot_id` — **top-level field** injected alongside the message, identifying which bot owns this job (used for lifecycle transitions and routing back to the correct `BotQueuesManager`)
   - `correspondent_id` — **top-level field** injected alongside the message, identifying which `CorrespondentQueue` holds the placeholder
   - `placeholder_message` — the full serialized `Message` placeholder dict (which contains message-oriented fields like `id`, `content`, `media_processing_id`, `sender`, etc., but **does not** contain routing IDs like `bot_id` or `correspondent_id` since those do not exist on the `Message` dataclass)
   - `guid` — used to locate the raw media file at `media_store/pending_media/<guid>`
   - `original_filename` *(optional)* — provided by the provider if available; used to assist processing (e.g. file extension hints)
   - `mime_type` — determines which processing pool to route the job to
6. **Processing completes**: The worker uses `bot_id` from the job to look up the correct `BotQueuesManager`, then calls `update_message_by_media_id(correspondent_id, guid, transcript)` on it. This locates the correct `CorrespondentQueue` and updates its `content` and `message_size`, then fires `_trigger_callbacks`. The job record is then **deleted from `media_processing_jobs`** and the raw media file is **deleted from disk**.

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

### `inject_placeholder(message: Message)`

A separate low-level method on `CorrespondentQueue` that directly inserts a pre-constructed `Message` object. Unlike `add_message()`, it:
- Does **not** generate a new message ID — uses the ID from the provided `Message`.
- Does **not** truncate content.
- Does **not** fire `_trigger_callbacks`.
- Does **not** re-enter the media pipeline.

Used exclusively by:
- **Crash recovery / bot startup** — re-injecting deserialized placeholders from `media_processing_jobs_holding` into the in-memory `CorrespondentQueue` when a bot connects and its jobs are moved back to `media_processing_jobs`.

### Required Change in `server.js` (Baileys Node.js Server)

First, add `downloadMediaMessage` to the Baileys imports at the top of the file:

```javascript
const {
    // ... existing imports ...
    downloadMediaMessage
} = require('@whiskeysockets/baileys');
```

Then, the current `processMessage` function discards media and captions:

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
    imageMessage:    { caption: msg.message.imageMessage?.caption },
    videoMessage:    { caption: msg.message.videoMessage?.caption },
    audioMessage:    { caption: null },  // audio has no caption
    documentMessage: { caption: msg.message.documentMessage?.caption },
    stickerMessage:  { caption: null },  // stickers have no caption
};

const mediaInfo = mediaTypes[messageType];  // messageType already resolved above (line 387)

if (mediaInfo !== undefined) {
    const guid = crypto.randomUUID();
    const mimetype = msg.message[messageType]?.mimetype;
    const filename = msg.message[messageType]?.fileName || null;
    const caption = mediaInfo.caption || '';
    const writePath = path.join('/app/media_store/pending_media', guid);

    // Enforce configurable application-level quota before downloading
    // `media_storage_quota_gb` is retrieved from the configuration collection in DB
    const configuredLimitGb = botConfig?.media_storage_quota_gb || 25; // fallback
    // Calculate threshold: limit - 2 GB, but ensure at least 1 GB is available for operations
    const stopWritingThresholdGb = Math.max(configuredLimitGb - 2, 1);
    const stopWritingThresholdMb = stopWritingThresholdGb * 1024;

    const { execSync } = require('child_process');
    try {
        const sizeOutput = execSync('du -sm /app/media_store/pending_media').toString().split('\t')[0];
        const currentSizeMb = parseInt(sizeOutput);
        
        if (currentSizeMb > stopWritingThresholdMb) {
            console.error(`Media quota exceeded (Current Size: ${currentSizeMb}MB, Threshold: ${stopWritingThresholdMb}MB). Rejecting download for ${guid}`);
            
            // Treat quota exhaustion exactly like a corrupt/failed download
            const baseType = messageType.replace('Message', ''); // e.g. 'image'
            const corruptMimetype = `media_corrupt_${baseType}`;
            
            // Send metadata back to Python, which routes it to CorruptMediaProcessor
            pushStatusToPython(userId, {
                type: 'new_message',
                message: {
                    guid: guid,
                    mime_type: corruptMimetype,
                    caption: caption,
                    original_filename: filename
                },
                // ... other message metadata ...
            });
            return; 
        }
    } catch (e) {
        console.warn(`Failed to check media directory size: ${e.message}`);
        // Let it proceed if du fails for some odd reason (fallback protection)
    }

    // Retry up to 3 times with exponential back-off (2s, 4s, 8s)
    let downloaded = false;
    let quotaExceeded = false;
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            const stream = await downloadMediaMessage(msg, 'stream', {});
            const writeStream = fs.createWriteStream(writePath);
            await new Promise((resolve, reject) => {
                stream.pipe(writeStream);
                writeStream.on('finish', resolve);
                writeStream.on('error', reject);
            });
            downloaded = true;
            break;
        } catch (err) {
            // Delete any partially-written file before retrying/aborting
            try { fs.unlinkSync(writePath); } catch (_) {}
            
            // Optional: fallback if disk physically fills completely
            if (err.code === 'ENOSPC') {
                console.error(`Media quota exceeded (ENOSPC). Rejecting download for ${guid}`);
                quotaExceeded = true;
                break; // Do not retry if disk is physically full
            }

            if (attempt < 3) {
                await new Promise(r => setTimeout(r, 2000 * Math.pow(2, attempt - 1)));
            } else {
                console.error(`Media download failed after 3 attempts for ${guid}: ${err.message}`);
            }
        }
    }

    if (downloaded) {
        // Return only metadata — no bytes cross the wire to Python
        return {
            ...existingFields,
            message: caption,
            media_processing_id: guid,
            mime_type: mimetype,
            original_filename: filename,
        };
    } else {
        // All retries failed OR quota exceeded — send as corrupted media
        // mediaType is e.g. "image", "video", "audio" (strip "Message" suffix)
        const shortType = messageType.replace('Message', '');
        return {
            ...existingFields,
            message: caption,                              // caption if exists, else ''
            media_processing_id: guid,
            mime_type: `media_corrupt_${shortType}`,       // e.g. "media_corrupt_image"
            original_filename: filename,
            _quota_exceeded: quotaExceeded                 // Optional marker for deeper logging upstream
        };
    }
}
```

The Python `whatsAppBaileys.py` provider passes the metadata (GUID, mime type, filename) to `add_message()`. No bytes are decoded or transferred.

## MediaProcessingService (Background Worker Pool)

A fixed-concurrency pool to avoid memory bloat and starvation across bots. **All media messages enter the pipeline identically** — every media message becomes a placeholder in the queue and a job in `media_processing_jobs`. The processor pool routing determines what happens next. Text messages bypass this service entirely and go straight to the queue.

### Processor Routing

| Mime type | Processor | Action |
|---|---|---|
| `audio/ogg`, `audio/mpeg` | Audio pool | speech-to-text API → transcript |
| `video/mp4`, `video/webm` | Video pool | vision/transcription API → description |
| `image/jpeg`, `image/png`, `image/webp` | Image pool | vision API → text description |
| `application/pdf`, `text/plain`, etc. | Document pool | text extraction API → plain text |
| `image/webp` (stickers) | Sticker pool | vision/metadata extraction → description |
| `media_corrupt_image`, `media_corrupt_audio`, `media_corrupt_video`, `media_corrupt_document`, `media_corrupt_sticker` | `CorruptMediaProcessor` | error handling (see below) |
| *anything else* (e.g. `text/calendar`)| `UnsupportedMediaProcessor` (default catch-all) | error handling (see below) |

### Corrupted Media Handling (`CorruptMediaProcessor`)

When `server.js` fails to download media after **3 retry attempts** (exponential back-off: 2s → 4s → 8s), it deletes any partially-written file and sends metadata to Python with `mime_type = "media_corrupt_<type>"` (e.g. `media_corrupt_image`, `media_corrupt_audio`, `media_corrupt_document`). The `content` field carries the original caption if one exists, otherwise an empty string. The message enters the queue as a placeholder like any other media message.

The `CorruptMediaProcessor` handles these jobs:
1. Deletes the media file from the shared volume (if one exists).
2. Moves the job to `media_processing_jobs_failed` with `error: "download failed — <type> corrupted"` for operator investigation.
3. Constructs the final message content:
   - If the placeholder has a caption: prepend `"[Corrupted <type> media could not be downloaded] "` to the existing caption.
   - If no caption: set `content = "[Corrupted <type> media could not be downloaded]"`.
4. Updates the placeholder in the `CorrespondentQueue` via `update_message_by_media_id` — sets the final `content`, clears `media_processing_id`, adjusts `message_size`, and fires `_trigger_callbacks` so the bot can acknowledge and respond to the failure.
5. Job is removed from `media_processing_jobs`.

### Unsupported Media Handling (`UnsupportedMediaProcessor`)

The `UnsupportedMediaProcessor` is the **default catch-all** — it handles any mime type that no other pool is configured to process. Since `server.js` sends the original mime type as-is (e.g. `text/calendar` (ICS files), `application/x-zip`), it has no knowledge of what the backend supports. The unsupported type detection happens naturally at the processor routing level: if no pool matches the mime type, it falls to the default.

The `UnsupportedMediaProcessor` follows the same pattern as `CorruptMediaProcessor`:
1. Deletes the media file from the shared volume.
2. Moves the job to `media_processing_jobs_failed` with `error: "unsupported mime type: <mime_type>"` for operator investigation.
3. Constructs the final message content:
   - If the placeholder has a caption: prepend `"[Unsupported <mime_type> media] "` to the existing caption.
   - If no caption: set `content = "[Unsupported <mime_type> media]"`.
4. Updates the placeholder in the `CorrespondentQueue` via `update_message_by_media_id` — sets the final `content`, clears `media_processing_id`, adjusts `message_size`, and fires `_trigger_callbacks`.
5. Job is removed from `media_processing_jobs`.

This keeps backend and provider fully decoupled — `server.js` never needs to know what mime types the backend supports.

### Concurrency Configuration

Pool definitions are loaded from the `bot_configurations` MongoDB collection, document `_id: "_mediaProcessorDefinitions"`. The document contains an array. Each entry specifies which `processorClass` handles the pool's messages and at what concurrency level, and also which mimeTypes are routed to that pool:

```json
[
  { "mimeTypes": ["audio/ogg", "audio/mpeg"], "processorClass": "AudioTranscriptionProcessor", "concurrentProcessingPoolSize": 2 },
  { "mimeTypes": ["video/mp4", "video/webm"], "processorClass": "VideoDescriptionProcessor", "concurrentProcessingPoolSize": 1 },
  { "mimeTypes": ["image/jpeg", "image/png"], "processorClass": "ImageVisionProcessor", "concurrentProcessingPoolSize": 3 },
  { "mimeTypes": ["application/pdf", "text/plain"], "processorClass": "DocumentProcessor", "concurrentProcessingPoolSize": 2 },
  { "mimeTypes": ["image/webp"], "processorClass": "StickerProcessor", "concurrentProcessingPoolSize": 2 },
  { "mimeTypes": ["media_corrupt_image", "media_corrupt_audio", "media_corrupt_video", "media_corrupt_document", "media_corrupt_sticker"], "processorClass": "CorruptMediaProcessor", "concurrentProcessingPoolSize": 1 },
  { "mimeTypes": [], "processorClass": "UnsupportedMediaProcessor", "concurrentProcessingPoolSize": 1 }
]
```

- `processorClass` — the Python class name that the service instantiates to handle messages in this pool.
- `mimeTypes: []` — the **catch-all** entry. Any mime type not matched by any other pool is routed here. There must be exactly one catch-all entry.

On startup, `MediaProcessingService` creates one worker pool per array entry, sized to `concurrentProcessingPoolSize`, instantiating the specified `processorClass`. Round-robin is applied **per pool** across bots to prevent starvation.

### Observability

To help diagnose backpressure and pipeline health, the `MediaProcessingService` logs the **queue depth per pool** on each poll cycle. By counting the number of pending jobs in `media_processing_jobs` grouped by `mime_type` (or mapped to their respective processor pool), operators can monitor if a specific pool (e.g., video processing) is falling behind.

### Memory Behavior During Processing

- **Audio**: Streamed from disk using a file handle (`open(file, 'rb')`). `httpx` uploads in chunks — the full audio is never loaded into Python heap. Genuinely low-memory.
- **Video**: Gemini's File API accepts a streaming upload (disk → network), returning a URI used for subsequent LLM calls — low-memory.
- **Image**: Base64-encoded before sending to vision APIs (full image bytes in memory). Acceptable given typical image sizes.

---

## Media Processor Interface

All processors inherit from `BaseMediaProcessor`, which encapsulates the full job lifecycle. Subclasses only implement the actual media-to-text conversion.

### `ProcessingResult` (Return Type)

```python
@dataclass
class ProcessingResult:
    content: str                          # Final message content for the queue
    failed_reason: Optional[str] = None   # If set, job is moved to _failed with this reason
```

### `BaseMediaProcessor` (Abstract Base Class)

```python
class BaseMediaProcessor(ABC):

    async def process_job(self, job: dict, all_bot_queues: Dict[str, BotQueuesManager], db: AsyncIOMotorDatabase):
        """Full shared lifecycle — called by the worker pool for each job."""
        bot_id = job["bot_id"]
        guid = job["guid"]
        mime_type = job["mime_type"]
        correspondent_id = job["correspondent_id"]
        caption = job["placeholder_message"].get("content", "")
        file_path = f"media_store/pending_media/{guid}"

        # Locate the correct BotQueuesManager for this bot
        bot_queues = all_bot_queues.get(bot_id)
        if not bot_queues:
            # Bot was stopped — queue no longer exists, leave for cleanup job
            logging.warning(f"BotQueuesManager not found for bot_id={bot_id}. Job left for cleanup.")
            return

        try:
            result = await self.process_media(file_path, mime_type, caption)
        except Exception as e:
            await self._handle_unhandled_exception(job, bot_queues, db, error=str(e))
            return

        # Always update the queue with the content and fire callbacks
        await bot_queues.update_message_by_media_id(correspondent_id, guid, result.content)

        if result.failed_reason:
            # Move job to _failed for investigation, delete media file
            await self._move_to_failed(job, db, error=result.failed_reason)
        else:
            # Normal success — remove the job, delete media file
            await self._remove_job(job, db)

        self._delete_media_file(file_path)

    @abstractmethod
    async def process_media(self, file_path: str, mime_type: str, caption: str) -> ProcessingResult:
        """Subclass implements actual processing. Returns a ProcessingResult."""
        ...
```

### Shared Lifecycle (`process_job`)

The base class handles all common operations in `process_job`:

1. **Extract job metadata** — `guid`, `mime_type`, `correspondent_id`, `caption` from the job record.
2. **Call `process_media()`** — the abstract method implemented by the subclass.
3. **Always update the queue** — call `update_message_by_media_id(correspondent_id, guid, result.content)` to set the final content, clear `media_processing_id`, adjust `message_size`, and fire `_trigger_callbacks`.
4. **Route the job based on `result.failed_reason`**:
   - **`None`** (normal success) → remove the job from `media_processing_jobs`.
   - **Set** (controlled failure) → move the job to `media_processing_jobs_failed` with the `failed_reason` as the `error` field.
5. **Delete the media file** from disk — always, regardless of success or failure.
6. **Unhandled exceptions** (`_handle_unhandled_exception`) — if `process_media()` raises, the job is moved to `media_processing_jobs_failed` with an `error` field containing the processor class name, the exception message, and the full stack trace (e.g. `"AudioTranscriptionProcessor raised ValueError: invalid audio format\n<traceback>"`). A generic error content is set on the queue (preserving caption if present), and the media file is deleted.

### Subclass Responsibilities

Each subclass only implements `process_media()` and returns a `ProcessingResult`:

| Processor Class | `process_media()` returns |
|---|---|
| `AudioTranscriptionProcessor` | `ProcessingResult(content=transcript)` |
| `VideoDescriptionProcessor` | `ProcessingResult(content=description)` |
| `ImageVisionProcessor` | `ProcessingResult(content=description)` |
| `CorruptMediaProcessor` | `ProcessingResult(content="[Corrupted <type>...] <caption>", failed_reason="download failed — <type> corrupted")` |
| `UnsupportedMediaProcessor` | `ProcessingResult(content="[Unsupported <mime_type>...] <caption>", failed_reason="unsupported mime type: <mime_type>")` |

> **Note**: Phase 1 stub processors also inherit from `BaseMediaProcessor` — they sleep for a configured duration and return `ProcessingResult(content="[Transcripted ...]")`. The base class handles everything else.

---

## Cleanup Job

A background job runs every **1 hour**. It scans all `CorrespondentQueue` instances for messages where `media_processing_id` is set and the message has been alive for more than **3 hours**.

For each stale placeholder found:
1. **Remove** the placeholder message from the `CorrespondentQueue`.
2. **Locate the matching job** and move it to `media_processing_jobs_failed`:
   - Found in `media_processing_jobs` → move and set `error`: `"message was transferred from media_processing_jobs to media_processing_jobs_failed by cleanup job"`
   - Found in `media_processing_jobs_holding` → move and set `error`: `"message was transferred from media_processing_jobs_holding to media_processing_jobs_failed by cleanup job"`
   - Found in neither → create a new record in `media_processing_jobs_failed` based on the placeholder message from `CorrespondentQueue` with added `error`: `"message was missing and created from scratch in media_processing_jobs_failed by cleanup job"`

**Additionally**, the cleanup job directly queries `media_processing_jobs_holding` for any job records older than **3 hours** — regardless of whether an in-memory queue placeholder exists. This catches stale jobs for bots that are currently **disconnected** (their in-memory queues are not active, so the queue scan above would never find them). For each such record found:
- Move it to `media_processing_jobs_failed` with `error`: `"job in media_processing_jobs_holding for stopped bot exceeded 3-hour threshold and was moved to media_processing_jobs_failed by cleanup job"`

- on any case, cleanup job attempts to delete the raw media file from disk.

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
- **Bot starts**: All holding jobs for that `bot_id` are moved from `media_processing_jobs_holding` → `media_processing_jobs`. The `placeholder_message` from each job is deserialized and re-injected into the correct `CorrespondentQueue` using `inject_placeholder(message)` — bypassing ID generation, content truncation, callback firing, and media pipeline re-entry. Processing then resumes.
- **Bot stops**: All active jobs for that `bot_id` are moved from `media_processing_jobs` → `media_processing_jobs_holding`.
  > **Note on in-flight jobs**: If a job is currently being processed at the moment the bot stops, the worker will attempt to call `update_message_by_media_id` on a `CorrespondentQueue` that no longer exists. This call is wrapped in a try/except — the error is logged and the job is left to be handled by the cleanup job.
- **Processing fails** (single attempt, no retries): Job is moved immediately to `media_processing_jobs_failed` for inspection with an added `error` property containing a text message describing the fail reason, and the raw media file is deleted from disk. No retries — each attempt consumes expensive tokens and resources, we don't want to retry error-prone messages.

> [!IMPORTANT]
> **Required fix — `IngestionService` final drain pass on bot stop**
> Currently `IngestionService.stop()` sets the stop event and exits immediately — if the ingester is in its 1-second sleep, it wakes up, sees the stop flag, and exits without draining remaining messages. Any messages that arrived since the last ingestion cycle are lost.
>
> **Fix**: After the background task finishes, run one final drain pass using `pop_ready_message()` before returning from `stop()`. This ensures only fully-processed messages are persisted — placeholders with `media_processing_id` still set are left untouched and will be handled by the job lifecycle (moved to holding on bot stop, cleaned up by the hourly cleanup job if stale).

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

The full routing chain uses three keys to locate the exact placeholder:

1. **`bot_id`** (from job) → look up the correct `BotQueuesManager` from the `Dict[str, BotQueuesManager]`.
2. **`correspondent_id`** (from job) → go directly to the correct `CorrespondentQueue` within that `BotQueuesManager`.
3. **`guid`** (from job) → search the `CorrespondentQueue`'s deque for the message matching `media_processing_id == guid`.
4. Updates `content`, `message_size`, clears `media_processing_id`, adjusts `_total_chars`, fires callbacks.
5. **The media processor never touches the message collections managed by `BotQueuesManager` or `IngestionService`** — it only operates on its own job lifecycle collections (`media_processing_jobs`, `media_processing_jobs_holding`, `media_processing_jobs_failed`).
6. If the `BotQueuesManager` is not found (bot was stopped) or the message is **not found** in the deque (queue was destroyed while the worker was in-flight), the update call is wrapped in a try/except — the error is logged, and the job is left for the cleanup job to handle.

### Placeholder Eviction Protection

The `CorrespondentQueue._enforce_limits()` method must **skip eviction of any message where `media_processing_id` is not `None`**. Placeholders are protected from being evicted by age, character count, or message count limits. They will only be removed by:
- Successful processing (via `update_message_by_media_id`).
- The hourly cleanup job (3-hour TTL — see Cleanup Job section).

This prevents a race condition where a flood of new messages could evict a placeholder before its transcript arrives.

---

## Ingestion Coordination: Skip-Pop Approach

The `IngestionService` uses a new `pop_ready_message()` method (replaces the old `pop_message()`) that iterates the internal `collections.deque` and returns the first message **without** a `media_processing_id`, leaving placeholders untouched. The underlying container remains a `deque` for O(1) appends/pops at both ends — the selective scan only adds a walk over the small number of in-flight placeholders, which is negligible.

Both the **regular ingestion cycle** and the **final drain on shutdown** use `pop_ready_message()`. This guarantees that:
- Only fully-processed messages are ever persisted to the database.
- Placeholders are never accidentally persisted as incomplete records.

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
3. For each job, it deserializes the `placeholder_message` and re-injects it into the correct `CorrespondentQueue` using `inject_placeholder(message)` — this bypasses ID generation, content truncation, callback firing, and media pipeline re-entry.
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
