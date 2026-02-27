# Multimedia Message Support Implementation Tasks

This document translates the `MultiMediaMessageTypeSupport.md` specification into actionable technical tasks.

## Implementation Overview Table

| Task ID | Title | Status |
| :--- | :--- | :--- |
| [T-001](#t-001-update-message-data-models) | Update Message Data Models | Pending |
| [T-002](#t-002-shared-staging-volume-setup) | Shared Staging Volume Setup | Pending |
| [T-003](#t-003-host-identity-sentry-uidgid) | Host Identity Sentry (UID/GID) | Pending |
| [T-004](#t-004-nodejs-media-streaming--quota) | Node.js Media Streaming & Quota | Pending |
| [T-005](#t-005-python-provider-contract-alignment) | Python Provider Contract Alignment | Pending |
| [T-006](#t-006-correspondentqueue-placeholder-support) | CorrespondentQueue Placeholder Support | Pending |
| [T-007](#t-007-eviction-protection-logic) | Eviction Protection Logic | Pending |
| [T-008](#t-008-media-processing-jobs-collections) | Media Processing Jobs Collections | Pending |
| [T-009](#t-009-mediaprocessingservice-core) | MediaProcessingService Core | Pending |
| [T-010](#t-010-basemediaprocessor--stub-implementations) | BaseMediaProcessor & Stub Implementations | Pending |
| [T-011](#t-011-specialized-error-processors) | Specialized Error Processors | Pending |
| [T-012](#t-012-fairness-first-worker-polling) | Fairness-First Worker Polling | Pending |
| [T-013](#t-013-ingestionservice-skip-pop-logic) | IngestionService Skip-Pop Logic | Pending |
| [T-014](#t-014-bot-lifecycle-recovery-hooks) | Bot Lifecycle Recovery Hooks | Pending |
| [T-015](#t-015-global-startup-recovery-sweep) | Global Startup Recovery Sweep | Pending |
| [T-016](#t-016-janitorial-cleanup-service) | Janitorial Cleanup Service | Pending |

---

## Detailed Tasks

### T-001: Update Message Data Models
- **Reference**: Spec Section: *Message Schema Change*, *Typed Data Models*
- **Action**:
    - Add `media_processing_id: Optional[str]` to `Message` dataclass in `queue_manager.py`.
    - Define `MediaProcessingJob` and `ProcessingResult` dataclasses in `infrastructure/models.py`.
    - Update `Message.__post_init__` to handle `media_processing_id` impacts on `message_size`.

### T-002: Shared Staging Volume Setup
- **Reference**: Spec Section: *Shared Media Volume & Storage Quota*
- **Action**:
    - Modify `docker-compose.yml` to define the `media_staging` volume.
    - Mount the volume to `whatsapp_baileys_server` and `backend` services at `/app/media_store/pending_media`.

### T-003: Host Identity Sentry (UID/GID)
- **Reference**: Spec Section: *Permissions & Ownership (The Deployment Sentry)*
- **Action**:
    - Update `./scripts/start.sh` to auto-detect `$OSTYPE` and `/proc/version`.
    - Standardize mapping: export `CURRENT_UID=1000` / `CURRENT_GID=1000` for virtualized hosts (msys/WSL).
    - Update `docker-compose.yml` to use `${CURRENT_UID}:${CURRENT_GID}` for service `user` fields.

### T-004: Node.js Media Streaming & Quota
- **Reference**: Spec Section: *Required Change in server.js*
- **Action**:
    - In `server.js`, import `crypto`, `util`, and `downloadMediaMessage`.
    - Implement quota check logic using `du -sm` (or running total as suggested in review).
    - Implement `downloadMediaMessage` streaming to disk with GUID filenames.
    - Add exponential back-off retry logic (3 attempts).
    - Handle quota-exceeded and download-fail cases by sending `media_corrupt_<type>` metadata.

### T-005: Python Provider Contract Alignment
- **Reference**: Spec Section: *Node -> Python WebSocket Payload Contract*
- **Action**:
    - Update `WhatsAppBaileysProvider._process_messages` to extract media metadata (`guid`, `mimetype`, `caption`).
    - Extend `BotQueuesManager.add_message` to accept these new optional parameters.

### T-006: CorrespondentQueue Placeholder Support
- **Reference**: Spec Section: *Provider Interface for Media Messages*
- **Action**:
    - Update `CorrespondentQueue.add_message` to handle media params:
        - If `media_processing_id` is set, suppress `_trigger_callbacks`.
        - Write job record to `media_processing_jobs` collection.
    - Implement `update_message_by_media_id(guid, content)`:
        - Locate placeholder, update content/size, clear `media_processing_id`.
        - Fire `_trigger_callbacks`.
    - Implement `inject_placeholder(message)` for recovery.

### T-007: Eviction Protection Logic
- **Reference**: Spec Section: *Placeholder Eviction Protection (The Eviction Rewrite)*
- **Action**:
    - Rewrite `CorrespondentQueue._enforce_limits` and `_evict_while`.
    - Ensure messages with `media_processing_id` are skipped during eviction.
    - Exclude protected messages from character/count limit arithmetic.

### T-008: Media Processing Jobs Collections
- **Reference**: Spec Section: *Job Collections Overview*
- **Action**:
    - Ensure MongoDB setup for `media_processing_jobs`, `media_processing_jobs_holding`, and `media_processing_jobs_failed`.
    - Create compound index on `bot_id`, `provider_name`, `correspondent_id`, `id` for `queues` tracking.

### T-009: MediaProcessingService Core
- **Reference**: Spec Section: *MediaProcessingService (Background Worker Pool)*
- **Action**:
    - Create `MediaProcessingService` in `services/`.
    - Initialize service in `main.py` lifespan.
    - Implement pull-based worker loop using `find_one_and_update` with `status="processing"`.

### T-010: BaseMediaProcessor & Stub Implementations
- **Reference**: Spec Section: *Media Processor Interface*, *Stub Implementations*
- **Action**:
    - Implement `BaseMediaProcessor` (ABC) with shared `process_job` lifecycle logic.
    - Handle result persistence, direct delivery attempts, and file cleanup in the base class.
    - Implement Phase 1 stub processors for Image, Audio, and Video (with configurable sleep/returns).

### T-011: Specialized Error Processors
- **Reference**: Spec Section: *Corrupted Media Handling*, *Unsupported Media Handling*
- **Action**:
    - Implement `CorruptMediaProcessor` to handle `media_corrupt_` mime types.
    - Implement `UnsupportedMediaProcessor` as the catch-all pool router.

### T-012: Fairness-First Worker Polling
- **Reference**: Spec Section: *Concurrency Configuration & Pull-Based Selection*
- **Action**:
    - Implement the "Single-Skip Two-Step" selection logic in the worker pool.
    - Ensure workers track `self.last_bot_id` to prioritize other bots' work on each cycle.

### T-013: IngestionService Skip-Pop Logic
- **Reference**: Spec Section: *Ingestion Coordination: Skip-Pop Approach*, *Required fix — IngestionService final drain*
- **Action**:
    - Implement `CorrespondentQueue.pop_ready_message()` to skip messages with `media_processing_id`.
    - Update `IngestionService._run` to use `pop_ready_message()`.
    - Implement a final drain pass in `IngestionService.stop()` to process remaining ready messages.

### T-014: Bot Lifecycle Recovery Hooks
- **Reference**: Spec Section: *Phase 2: Bot-Specific Transitions*
- **Action**:
    - Update `BotLifecycleService` (or SessionManager) to trigger media reaping on connection.
    - Implement `BotQueuesManager.reap_and_promote_jobs(bot_id)`:
        - Atomic Reaping (`status="completed"`) → `inject_placeholder` + `update_message_by_media_id`.
        - Promotion (`status="pending/processing"`) → move to active collection.
    - Implement job movement to `_holding` on bot disconnect.

### T-015: Global Startup Recovery Sweep
- **Reference**: Spec Section: *Phase 1: Global Startup Recovery (The Init Sweep)*
- **Action**:
    - Add startup hook in `main.py` (or `MediaProcessingService.initialize`) to move all active jobs to holding.
    - Reset `processing` records back to `pending`.

### T-016: Janitorial Cleanup Service
- **Reference**: Spec Section: *Phase 3: Janitorial Sweep (The Double-Lock Cleanup)*
- **Action**:
    - Implement an hourly background task to:
        - Purge stale placeholders and move jobs to `_failed`.
        - Sweep DB collections for jobs older than 3 hours.
        - Run Orphan File Cleanup on the shared volume (GUID check).
