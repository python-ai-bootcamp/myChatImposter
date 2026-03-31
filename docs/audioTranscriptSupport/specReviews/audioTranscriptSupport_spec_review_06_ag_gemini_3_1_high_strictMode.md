# Audio Transcript Support Specification Review
## Review ID: `06_ag_gemini_3_1_high_strictMode`

## Summary of Findings

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | `ATS-06-01` | `BaseModelProvider` Missing `initialize()` Method Crashing Factory | [Details](#ats-06-01-basemodelprovider-missing-initialize-method-crashing-factory) | READY |
| High | `ATS-06-02` | `format_processing_result` Missing `failed_reason` Parameter in Signature | [Details](#ats-06-02-format_processing_result-missing-failed_reason-parameter-in-signature) | READY |
| Medium | `ATS-06-03` | Async Cancellation Hazard leaking Resources in `finally` Block Cleanup | [Details](#ats-06-03-async-cancellation-hazard-leaking-resources-in-finally-block-cleanup) | READY |

---

## Detailed Review Items

### `ATS-06-01`: `BaseModelProvider` Missing `initialize()` Method Crashing Factory
- **Priority**: High
- **ID**: `ATS-06-01`
- **Title**: `BaseModelProvider` Missing `initialize()` Method Crashing Factory
- **Detailed Description**:
  The spec instructs that all providers should call an `await provider.initialize()` step immediately after instantiation inside `create_model_provider` within `services/model_factory.py`. This is intended to ensure external HTTP clients are started for the new provider structure.

  However, since `create_model_provider` is a centralized polymorphic factory returning any subclass of `BaseModelProvider` (including existing Chat and Moderation providers like `ChatCompletionProvider`), executing `await provider.initialize()` for all providers globally will cause a runtime crash. Specifically, `BaseModelProvider` (and its existing subclasses) currently lacks an `initialize()` method. Without adding a base method or an attribute check, instantiating standard LLM providers will immediately throw an `AttributeError`, breaking the bot globally.
- **Status**: PENDING
- **Required Actions**: 

---

### `ATS-06-02`: `format_processing_result` Missing `failed_reason` Parameter in Signature
- **Priority**: High
- **ID**: `ATS-06-02`
- **Title**: `format_processing_result` Missing `failed_reason` Parameter in Signature
- **Detailed Description**:
  The spec dictates refactoring `format_processing_result` in `media_processors/base.py` to add logic that "conditionally [prepends] '{MediaType} Transcription: ' to the content. This prefix injection must only occur if `unprocessable_media` is False and `failed_reason` is empty."

  However, an examination of `format_processing_result`'s current signature reveals it does not accept a `failed_reason` argument (it only takes `content`, `caption`, `original_filename`, and `unprocessable_media`). In the `BaseMediaProcessor.process_job` flow, `failed_reason` is appended *after* formatting occurs. 

  Asking the developer to check `failed_reason` inside `format_processing_result()` is currently impossible because the parameter is completely absent from the function. 
- **Status**: READY
- **Required Actions**: Update the specification to remove the requirement to evaluate `failed_reason` inside `format_processing_result()`. Instruct the developer to strictly check `if not unprocessable_media:` for injecting the prefix. Furthermore, instruct the developer to modify the fallback error handling in `BaseMediaProcessor._handle_unhandled_exception` to explicitly pass `unprocessable_media=True` (it currently defaults to False) so that unhandled system errors safely bypass the prefix injection logic.

---

### `ATS-06-03`: Async Cancellation Hazard leaking Resources in `finally` Block Cleanup
- **Priority**: Medium
- **ID**: `ATS-06-03`
- **Title**: Async Cancellation Hazard leaking Resources in `finally` Block Cleanup
- **Detailed Description**:
  The spec's code snippet for `SonioxAudioTranscriptionProvider.transcribe_audio` orchestrates a strict `try/finally` block to protect Soniox server quotas:
  ```python
  finally:
      if transcription:
          await self.client.stt.delete(transcription.id)
      if file:
          await self.client.files.delete(file.id)
  ```
  While logically sound, this implementation has a critical `asyncio` flaw. `AudioTranscriptionProcessor.process_media` runs inside `asyncio.wait_for(...)` within the base processor (which enforces a timeout of e.g. 300 seconds). If the Soniox transcription times out, `process_media` is cancelled, injecting an `asyncio.CancelledError` into the task.

  When the task enters the `finally` block, any subsequent `await` calls will immediately re-raise the `CancelledError` because the driving event loop detects the task is already cancelled. Thus, `await self.client.stt.delete(...)` will instantaneously abort, and the cleanup operations will never execute, resulting in silent network resource leaks.
- **Status**: READY
- **Required Actions**: Update the specification code snippet to instruct the developer to wrap the network cleanup commands inside an asynchronous closure, and execute it using `asyncio.create_task(...)` within the `finally` block of the `transcribe_audio` method. The specification must explain that this approach creates a fire-and-forget background task attached natively to the event loop, safely bypassing the parent task's `CancelledError` and guaranteeing the remote resources are successfully wiped.
