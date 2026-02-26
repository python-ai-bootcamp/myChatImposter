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

**Runtime retrieval path (mandatory):** the Python backend resolves `media_storage_quota_gb` from MongoDB and passes it to the Node.js Baileys service in the `/initialize` payload. Node.js does not read this value directly from MongoDB.

```yaml
# docker-compose.yml
services:
  whatsapp_baileys_server:
    user: "${CURRENT_UID}:${CURRENT_GID}"  # Auto-detected by ./scripts/start.sh
    volumes:
      - media_staging:/app/media_store/pending_media

  backend:
    user: "${CURRENT_UID}:${CURRENT_GID}"  # Same UID/GID as host user
    volumes:
      - media_staging:/app/media_store/pending_media

volumes:
  media_staging:
```

### Permissions & Ownership (The Deployment Sentry)
To avoid "Permission Denied" errors (EACCES) on shared volumes, both containers must match the identity of the host user who owns the project files. 

- **The Strategy**: Use dynamic environment variables `${CURRENT_UID}:${CURRENT_GID}` for the `user` field in `docker-compose.yml`.
- **The Rationale**: Since bind mounts (like `baileys_store`) inherit the host's UID/GID, hardcoding `1000:1000` is risky if the host VM uses a different ID.
- **The Implementation**: `./scripts/start.sh` must auto-detect the host identity (`id -u` and `id -g`) and export `CURRENT_UID` / `CURRENT_GID` into `.env` **before** `docker compose up`.
- **The Result**: Files written by the Node.js server are immediately reachable and manageable by the Python `MediaProcessingService` regardless of the host OS configuration.

> [!TIP]
> This pattern ensures "zero-touch" deployment security—the system auto-sets its permissions the moment you run the startup command. 🛡️

---

## Flow for a Media Message

1. **Node.js receives media** → generates a GUID, streams the media to disk at `media_store/pending_media/<guid>` using Baileys' streaming API (`downloadMediaMessage(msg, 'stream')`). Media bytes never fully load into Node.js memory.
2. **Node.js sends metadata to Python** via WebSocket — only the GUID, mime type, caption, and original filename. No media bytes cross the wire.
3. **Python provider receives metadata** → calls `BotQueuesManager.add_message()` with the media params (GUID, mime type, caption, filename).
4. **Placeholder insertion**: `BotQueuesManager` adds a `Message` to the `CorrespondentQueue` with `content=<caption>` (or `""`) and `media_processing_id=<guid>`. No file validation is performed — if the file is missing or corrupt, the processor handles the implications.
5. **Non-blocking processing trigger**: `BotQueuesManager.add_message()` writes a job record to the **`media_processing_jobs`** MongoDB collection. This is the job submission — `MediaProcessingService` worker pools (each with a dedicated media processor per mime type) poll this collection for work. Each job record contains:
   - `bot_id` — **top-level field** injected alongside the message, identifying which bot owns this job (used for lifecycle transitions and routing back to the correct `BotQueuesManager`)
   - `correspondent_id` — **top-level field** injected alongside the message, identifying which `CorrespondentQueue` holds the placeholder
   - `placeholder_message` — the full serialized `Message` placeholder dict (which contains message-oriented fields like `id`, `content`, `media_processing_id`, `sender`, etc., but **does not** contain routing IDs like `bot_id` or `correspondent_id` since those do not exist on the `Message` dataclass)
   - `guid` — used to locate the raw media file at `media_store/pending_media/<guid>`
   - `original_filename` *(optional)* — provided by the provider if available; used to assist processing (e.g. file extension hints)
   - `mime_type` — determines which processing pool to route the job to
   - `status` — **"pending"** (default), **"processing"** (claimed by worker), or **"completed"** (result saved, awaiting delivery)
   - `result` — *(optional)* The finalized transcript or description text, populated when `status == "completed"`

6. **Worker claims job**: The `MediaProcessingService` uses an **atomic `find_one_and_update`** to claim a job where `status == "pending"`. It sets `status = "processing"` and assigns a `worker_id`. This atomic action ensures that even if 100 jobs move to the active queue at once, no two workers will ever pick up the same task. If a bot resets mid-job, the job remains in `"processing"` state, signaling other workers to stay away.

7. **Processing completes (Result Persistence)**: The worker performs its AI mission, then **immortalizes the result** in the database. It attempts an atomic update on the job record to set `status = "completed"` and `result = transcript`. It tries the `media_processing_jobs` (active) collection first; if not found (bot stopped), it tries `media_processing_jobs_holding`.

8. **Final Reporting (Delivery vs. Reaping)**: Once the result is safely persisted in the DB, the worker attempts to complete the mission:
   - **Case A: Direct Worker Delivery** (Bot is Active): The worker locates the `BotQueuesManager`, calls `update_message_by_media_id(correspondent_id, guid, transcript)`, and **deletes the job**.
   - **Case B: Recovery Bot Reaping** (Bot is Stopped): The worker finds no active bot and gracefully exits. The job remains in the **`media_processing_jobs_holding`** collection with `status="completed"`. When the bot eventually restarts, it **reaps** the result from the holding collection, injects the placeholder, updates its queue, and **deletes the job**.
   - On completion (via either path), the **worker** deletes the raw media file from the shared disk.

### Media Flow Sequence Diagram

```mermaid
sequenceDiagram
    participant P as Chat Provider (Node.js)
    participant FS as Shared Staging Volume
    participant BQM as BotQueuesManager
    participant Q as CorrespondentQueue
    participant DB as MongoDB (Job Collections)
    participant W as Media Processing Worker

    Note over P, W: 1. Media Ingestion
    P->>FS: 1. Stream media file to disk (GUID)
    P->>BQM: 2. Send metadata via WebSocket
    BQM->>Q: 3-4. Insert Placeholder Message (media_processing_id=GUID)
    BQM->>DB: 5. Insert Job (status="pending")
    
    Note over DB, W: 2. Worker Processing
    W->>DB: 6. Claim Job (find_one_and_update, status="processing")
    W->>FS: Read media file from disk
    Note over W: Process Media using APIs
    W->>DB: 7. Persist Result (status="completed")
    
    Note over BQM, W: 3. Final Delivery
    alt Case A: Bot is Active (Direct Delivery)
        W->>BQM: 8a. update_message_by_media_id(transcript)
        BQM->>Q: Update placeholder with final text
        W->>DB: Delete Job
    else Case B: Bot is Stopped (Recovery Reaping)
        Note right of DB: Worker exits. Result stays in DB.
        BQM-->>DB: 8b. Bot starts later, queries holding jobs
        BQM->>Q: inject_placeholder(message)
        BQM->>Q: update_message_by_media_id(transcript)
        BQM->>DB: Delete Job
    end
    
    W->>FS: Delete raw media file from disk
```

---

## Node -> Python WebSocket Payload Contract

This is a wire-level contract (cross-runtime boundary): **Node.js -> WebSocket JSON -> Python**.

### Text message payload

Required fields:
- `provider_message_id: str`
- `sender: str`
- `message: str`
- `direction: "incoming" | "outgoing"`
- `originating_time: int`

Optional fields:
- `display_name: str | null`
- `group: object | null`
- `alternate_identifiers: list[str]`
- `recipient_id: str | null`
- `actual_sender: object | null`
- `media_processing_id: null`
- `mime_type: null`
- `original_filename: null`

### Media message payload (download succeeded)

Required fields:
- All required text fields above
- `message: str` (caption, or `""` if none)
- `media_processing_id: str` (GUID)
- `mime_type: str`

Optional fields:
- `original_filename: str | null`

### Corrupt/failed-download media payload

Required fields:
- All required text fields above
- `message: str` (caption, or `""`)
- `media_processing_id: str` (GUID)
- `mime_type: "media_corrupt_<type>"` (where `type` is one of: `image`, `video`, `audio`, `document`, `sticker`)

Optional fields:
- `original_filename: str | null`
- `_quota_exceeded: bool` (diagnostic marker)

Python should validate this WS payload contract (preferably via an internal typed model) before mapping to `BotQueuesManager.add_message(...)`.

---

## Provider Interface for Media Messages

The existing `add_message()` method on `BotQueuesManager` is extended with optional media parameters:

```python
async def add_message(
    self,
    correspondent_id: str,                  # Required routing key (queue owner)
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

First, add `crypto`, `exec` (from `child_process`), and `util` to the imports at the top of the file:

```javascript
const crypto = require('crypto');
const util = require('util');
const execAsync = util.promisify(require('child_process').exec);
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

    // Enforce configurable application-level quota before downloading.
    // `media_storage_quota_gb` is provided by backend in `/initialize` payload.
    const configuredLimitGb = session.providerConfig?.media_storage_quota_gb || 25; // fallback
    // Calculate threshold: limit - 2 GB, but ensure at least 1 GB is available for operations
    const stopWritingThresholdGb = Math.max(configuredLimitGb - 2, 1);
    const stopWritingThresholdMb = stopWritingThresholdGb * 1024;

    try {
        // ASYNC to prevent freezing the single-threaded event loop
        const { stdout } = await execAsync('du -sm /app/media_store/pending_media');
        const sizeOutput = stdout.toString().split('\t')[0];
        const currentSizeMb = parseInt(sizeOutput, 10);
        
        if (currentSizeMb > stopWritingThresholdMb) {
            console.error(`Media quota exceeded (Current Size: ${currentSizeMb}MB, Threshold: ${stopWritingThresholdMb}MB). Rejecting download for ${guid}`);
            
            // Treat quota exhaustion exactly like a corrupt/failed download
            const baseType = messageType.replace('Message', ''); // e.g. 'image'
            const corruptMimetype = `media_corrupt_${baseType}`;
            
            return {
                ...existingFields, // spread common metadata: provider_message_id, sender, direction, time, etc.
                message: caption,
                media_processing_id: guid,
                mime_type: corruptMimetype,
                original_filename: filename,
                _quota_exceeded: true
            };
        }
    } catch (error) {
        console.error(`Failed to calculate media directory size for ${guid}: ${error.message}. Rejecting download.`);
        const baseType = messageType.replace('Message', '');
        const corruptMimetype = `media_corrupt_${baseType}`;
        return {
            ...existingFields, // spread common metadata
            message: caption,
            media_processing_id: guid,
            mime_type: corruptMimetype,
            original_filename: filename,
            _quota_error: true // diagnostic marker for system error
        };
    }
    // --- Proceed with Retry Logic ---    // Retry up to 3 times with exponential back-off (2s, 4s, 8s)
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
            ...existingFields, // spread common metadata (sender, id, time, etc.)
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
            ...existingFields, // spread common metadata
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

### Service Ownership and Lifecycle Wiring

- `MediaProcessingService` is initialized in backend `main.py` lifespan during startup (after MongoDB init), stored on global state (e.g. `global_state.media_processing_service`), and started before active bots are launched.
- On startup, it performs the same recovery phase described in this spec (`media_processing_jobs -> media_processing_jobs_holding`, then `processing -> pending`).
- It is stopped during backend shutdown in lifespan teardown.
- Bot lifecycle hooks are owned by `BotLifecycleService`:
  - on bot connect: trigger holding->active media transition/reaping flow for that bot
  - on bot disconnect: trigger active->holding media transition for that bot
- Runtime resolver API for queue routing:
  - `get_bot_queues(bot_id) -> Optional[BotQueuesManager]`
  - implementation uses global state maps (`active_bots` and `chatbot_instances`) to resolve `bot_id -> SessionManager -> bot_queues_manager`

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

When `server.js` fails to download media after **3 retry attempts** (exponential back-off: 2s → 4s → 8s), it deletes any partially-written file and sends metadata to Python with `mime_type = "media_corrupt_<type>"` (where `<type>` is `image`, `video`, `audio`, `document`, or `sticker`). The `content` field carries the original caption if one exists, otherwise an empty string. The message enters the queue as a placeholder like any other media message.

The `CorruptMediaProcessor` handles these jobs:
1. Deletes the media file from the shared volume (if one exists).
2. Moves the job to `media_processing_jobs_failed` with `error: "download failed — <type> corrupted"` (e.g., `image corrupted`) for operator investigation.
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

        try:
            result = await self.process_media(file_path, mime_type, caption)
        except Exception as e:
            await self._handle_unhandled_exception(job, db, error=str(e))
            return

        # PERSISTENCE-FIRST: write durable state before touching in-memory queue
        persisted = await self._persist_result_first(job, result, db)  # active first, then holding
        if not persisted:
            self._delete_media_file(file_path)
            return

        # Best-effort direct delivery if bot is currently active
        bot_queues = all_bot_queues.get(bot_id)
        if bot_queues:
            await bot_queues.update_message_by_media_id(correspondent_id, guid, result.content)

            # Direct delivery path: remove completed job only after successful queue update
            if not result.failed_reason:
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
3. **Persist result first (durable state)** — write result to job document (active collection first, then holding fallback) before any in-memory queue update.
4. **Best-effort in-memory delivery** — if bot queue exists, call `update_message_by_media_id(...)`; if bot queue does not exist, leave persisted result for recovery reaping on next bot startup.
5. **Direct delivery cleanup** — if in-memory update succeeds on an active bot, remove the completed job.
6. **Delete the media file** from disk — always, regardless of success/failure path.
7. **Unhandled exceptions** (`_handle_unhandled_exception`) — if `process_media()` raises, move job to `media_processing_jobs_failed` with full error context; set generic queue error content only if queue is available; always delete media file.

### Subclass Responsibilities

Each subclass only implements `process_media()` and returns a `ProcessingResult`:

| Processor Class | `process_media()` returns |
|---|---|
| `AudioTranscriptionProcessor` | `ProcessingResult(content=transcript)` |
| `VideoDescriptionProcessor` | `ProcessingResult(content=description)` |
| `ImageVisionProcessor` | `ProcessingResult(content=description)` |
| `CorruptMediaProcessor` | `ProcessingResult(content="[Corrupted <type>...] <caption>", failed_reason="download failed — <type> corrupted")` |
| `UnsupportedMediaProcessor` | `ProcessingResult(content="[Unsupported <mime_type>...] <caption>", failed_reason="unsupported mime type: <mime_type>")` |

#### Anti-Starvation Rule (Mandatory Timeouts)
To prevent workers from becoming permanently marooned by hanging external API calls (e.g., an OpenAI vision request that never returns), **every** external I/O operation inside `process_media()` must be wrapped in a strict `asyncio.wait_for()` timeout.

```python
import asyncio

async def process_media(self, file_path: str, mime_type: str, caption: str) -> ProcessingResult:
    try:
        # Force the API call to complete or fail within 60 seconds
        response = await asyncio.wait_for(api_client.process_image(encoded_image), timeout=60.0)
        return ProcessingResult(content=response.text)
    except asyncio.TimeoutError:
        # The timeout breaks the hang. We catch it and return a controlled failure.
        # The worker loop continues, capacity is preserved!
        return ProcessingResult(
            content="[Processing timed out]",
            failed_reason="API_TIMEOUT: Vision processing exceeded 60 seconds"
        )
```
If this rule is ignored, a hanging request permanently reduces the finite worker pool capacity by 1. Three such hangs would reduce a 3-worker pool to zero, freezing all media processing until the container is restarted.

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

**Additionally**, the cleanup job directly queries `media_processing_jobs` and `media_processing_jobs_holding` for any job records older than **3 hours**. This catches:
- Stale jobs for bots that are currently **disconnected** (in `_holding`).
- "Zombie" jobs stuck in `processing` state due to a worker crash.

For each such record found:
- Move it to `media_processing_jobs_failed` with `error`: `"TIMED_OUT: Job exceeded 3-hour threshold and was moved to failed by cleanup job"`.
- Attempt to delete the raw media file from disk.
- If an in-memory placeholder exists, remove it from the `CorrespondentQueue`.

---

## Job Collection Lifecycle

Three MongoDB collections manage job state, mirroring the `async_message_delivery_queue_manager` pattern:

| Collection | Purpose |
|---|---|
| `media_processing_jobs` | Active jobs — bot is running and jobs are being processed |
| `media_processing_jobs_holding` | Holding jobs — bot is stopped, jobs are paused |
| `media_processing_jobs_failed` | Failed jobs — processing failed on single attempt |

### Lifecycle Transitions
- **App startup (init phase)**: A global sweep performs a two-stage recovery:
  1. Moves **all** records from `media_processing_jobs` to `media_processing_jobs_holding`.
  2. Perform an `update_many` on `media_processing_jobs_holding` to set any record with `status: "processing"` back to `status: "pending"`.
  This ensures no orphaned jobs remain stuck in an unclaimable state due to a previous system crash.
- **Bot starts (Recovery Bot Reaping)**: When a `BotQueuesManager` initializes, it queries `media_processing_jobs_holding` for its `bot_id`. For every job found, it must **first call `inject_placeholder(message)`** using the job's `placeholder_message` to seed the empty queue. Only *after* injecting the placeholder does the bot evaluate the job's `status`:
  - **`status == "completed"`**: The bot **reaps** the result from the job, updates the newly-injected placeholder instantly via `update_message_by_media_id`, fires callbacks (triggering the AI), and **deletes the job**.
  - **`status == "processing"`**: The job is moved back to `media_processing_jobs`. An orphaned worker is still working on it. The bot waits for **Direct Worker Delivery**.
  - **`status == "pending"`**: The job is moved to `media_processing_jobs` to await a worker claim.
- **Bot stops**: All active jobs for that `bot_id` are moved from `media_processing_jobs` → `media_processing_jobs_holding`.
  - > **Note on in-flight jobs**: If a job is currently being processed at the moment the bot stops, the worker will finish and follow the **Persistence-First path**, saving the result into `_holding` for later reaping.
- **Processing fails** (single attempt, no retries): Job is moved immediately to `media_processing_jobs_failed` for inspection with an added `error` property and the raw media file is deleted. No retries.

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
   - `update_message_by_media_id` contract:
     - locate by `media_processing_id`
     - compute `old_size` / `new_size`
     - update `content`, `message_size`, clear `media_processing_id`
     - update `_total_chars = _total_chars - old_size + new_size`
     - fire callbacks exactly once
     - return structured result (e.g. `updated`, `not_found`)
5. **The media processor follows the Persistence-First path**:
   - Every result is saved to the Job Document (status set to `"completed"`) *before* attempting in-memory queue updates.
   - The worker attempts to update the job record in the `media_processing_jobs` collection; if 0 documents were updated, it attempts the same update in `media_processing_jobs_holding`.
6. **Handling Job Abandonment (The "Late-Returning Hero")**: If both the `active` and `holding` job updates modify 0 documents (likely because the cleanup job dead-lettered the job due to a timeout):
   - The worker logs a `WARNING`: `"Job record missing for GUID <guid>. Task result abandoned — likely timed out."`
   - The worker deletes the raw media file and exits. No further action is taken.
7. If the `BotQueuesManager` is not found (bot was stopped), the worker logs the success and terminates. The result is already safe in MongoDB.
8. If the `BotQueuesManager` is found but the message is **not found** in the deque (e.g. queue was reset), the update call is wrapped in a try/except — the worker logs the issue and deletes the job (as it's unrecoverable without a placeholder).

### Placeholder Eviction Protection (The Eviction Rewrite)

The `CorrespondentQueue` enforces memory limits (max messages, max characters) by popping the oldest messages. However, placeholders with active `media_processing_id`s represent pending work and **must be protected** from routine eviction.

**The Flaw in `popleft()`:**
The current `_evict_while` helper blindly uses `self._messages.popleft()`. If a protected placeholder sits at index `0`, the eviction loop would either break immediately (allowing the queue to grow infinitely past its limits) or enter an infinite loop trying to evict an unevictable message.

**The Fix:**
The eviction/limit logic must treat protected placeholders as fully excluded from limit arithmetic:
- messages with `media_processing_id is not None` are **non-evictable**
- and are **not counted** in effective limit evaluation (`max_messages`, `max_characters`, age retention)
- effective limits are computed only on the unprotected subset
- eviction removes only oldest eligible unprotected messages when the unprotected subset exceeds limits

Placeholders will only ever be removed by:
1. Successful worker delivery (replaced by final content).
2. The 3-hour background `cleanup` job (expired/stale).
3. The `CorruptMediaProcessor` or `UnsupportedMediaProcessor` (failed).

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
2. As each bot connects, its `BotQueuesManager` queries the holding collection. 
3. **Crucial Seeding Step:** For *every* job found (regardless of status), the bot deserializes the `placeholder_message` and re-injects it into the `CorrespondentQueue` using `inject_placeholder(message)`. This bypasses ID generation and callbacks, securely seeding the empty queue.
   - After all placeholders are injected for a correspondent, force monotonic IDs:
     - `next_id = max(next_id, max(injected_placeholder_ids) + 1)`
4. The bot then evaluates the status:
   - **`completed`**: Reaps the result immediately using `update_message_by_media_id` and fires callbacks.
   - **`pending` / `processing`**: Moves them back to the active collection for worker pools to (re)claim and process.
5. The job record is deleted and the media file is removed from disk once processing and delivery complete successfully.

**MongoDB is the source of truth for crash recovery — no data is lost.**

To prevent ID collision persistence bugs from escaping to storage, the `queues` collection must enforce:
- unique compound index on (`bot_id`, `provider_name`, `correspondent_id`, `id`)
- do **not** enforce uniqueness on `id` alone (it is only unique within correspondent scope)

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
