# Audio Transcript Support Specification Review

## Summary of Findings

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | `ATS-04-01` | Factory Architecture Gap for Token Tracker Injection | [#ats-04-01-factory-architecture-gap-for-token-tracker-injection](#ats-04-01-factory-architecture-gap-for-token-tracker-injection) | READY |
| High | `ATS-04-05` | Missing Prefix Injection Logic in `format_processing_result` | [#ats-04-05-missing-prefix-injection-logic-in-format_processing_result](#ats-04-05-missing-prefix-injection-logic-in-format_processing_result) | READY |
| Medium | `ATS-04-03` | Contradictory Error Handling Expectations for `unprocessable_media` | [#ats-04-03-contradictory-error-handling-expectations-for-unprocessable-media](#ats-04-03-contradictory-error-handling-expectations-for-unprocessable-media) | READY |
| Low | `ATS-04-04` | Misleading Schema Extraction Dynamic Keys Reference | [#ats-04-04-misleading-schema-extraction-dynamic-keys-reference](#ats-04-04-misleading-schema-extraction-dynamic-keys-reference) | PENDING |

---

## Detailed Review Items

### `ATS-04-01`: Factory Architecture Gap for Token Tracker Injection
- **Priority**: High
- **ID**: `ATS-04-01`
- **Title**: Factory Architecture Gap for Token Tracker Injection
- **Detailed Description**: 
  The specification correctly notes that `AudioTranscriptionProvider` does not inherit from `LLMProvider`. However, it instructs the developer to update `create_model_provider` in `services/model_factory.py` by adding an `elif isinstance(provider, AudioTranscriptionProvider): return provider` branch and injecting a `token_tracker` closure via `set_token_tracker()`. 
  The design gap is that in `services/model_factory.py`, the `TokenConsumptionService` is currently only instantiated *inside* the `if isinstance(provider, LLMProvider):` block. If `AudioTranscriptionProvider` does not enter this block, it does not have access to the `token_service` variable to create the closure. The spec fails to instruct the developer to refactor the `TokenConsumptionService` initialization out of the `LLMProvider` block so it is accessible to the custom `token_tracker` closure for the audio transcription provider.
- **Status**: READY
- **Required Actions**: Refactor initialization in `model_factory.py`. Extract `TokenConsumptionService` and its `get_global_state()` dependency out of the `isinstance(provider, LLMProvider)` type-check block so it is initialized once and available to be tracked within both the LangChain callback configuration and the custom `token_tracker` async closure inside the new `AudioTranscriptionProvider` branch.

---

### `ATS-04-03`: Contradictory Error Handling Expectations for `unprocessable_media`
- **Priority**: Medium
- **ID**: `ATS-04-03`
- **Title**: Contradictory Error Handling Expectations for `unprocessable_media`
- **Detailed Description**: 
  The "Test Expectations" section explicitly states: "Verify the `asyncio.TimeoutError` exception path correctly applies `unprocessable_media`." However, as dictated by the sibling architecture, `asyncio.TimeoutError` is enforced and caught externally by `BaseMediaProcessor.process_job()` via `asyncio.wait_for`. Because the timeout is handled in the base class (which does not set `unprocessable_media=True`), it is architecturally impossible for the concrete `AudioTranscriptionProcessor` to fulfill this test expectation. Expecting the child processor to handle this and apply the flag is a fundamental misunderstanding of the base class lifecycle.
- **Status**: READY
- **Required Actions**: Update `BaseMediaProcessor.process_job()`'s `asyncio.TimeoutError` exception block to explicitly include `unprocessable_media=True` when returning the `ProcessingResult`. This globally enforces the test expectation uniformly across all media processors.

---

### `ATS-04-05`: Missing Prefix Injection Logic in `format_processing_result`
- **Priority**: High
- **ID**: `ATS-04-05`
- **Title**: Missing Prefix Injection Logic in `format_processing_result`
- **Detailed Description**: 
  The codebase currently lacks the logic to inject the semantic medium prefix (e.g. `"Audio Transcription: "`). The function `format_processing_result` in `media_processors/base.py` currently blindly bracket-wraps whatever content it receives. Without this prefix injection logic, the `unprocessable_media` flag is functionally dead, as its entire purpose is to bypass a prefix that doesn't actually exist on generation.
- **Status**: READY
- **Required Actions**: Refactor `format_processing_result` in `media_processors/base.py` to accept a `mime_type: str` parameter. Add logic inside the function to dynamically determine the media type from the mime type and prepend `{MediaType} Transcription: ` to the content *only if* `unprocessable_media` is `False` and no `failed_reason` exists. Update all internal `base.py` calls to pass the job's `mime_type` into this formatter.

---

### `ATS-04-04`: Misleading Schema Extraction Dynamic Keys Reference
- **Priority**: Low
- **ID**: `ATS-04-04`
- **Title**: Misleading Schema Extraction Dynamic Keys Reference
- **Detailed Description**: 
  The "Configuration" overview section claims that "`get_configuration_schema` in `routers/bot_management.py` dynamic tier extraction covers this if implemented using `.keys()`." 
  However, the `get_configuration_schema` implementation (around line 365) does not dynamically use `.keys()`; it utilizes a hardcoded array list (`for prop_name in ['high', 'low', 'image_moderation', 'image_transcription']:`). While the specification correctly catches this mechanically in Step 3 of the Checklist ("you MUST also manually append..."), the initial overview statement is misleading and factually inaccurate regarding the current codebase state.
- **Status**: PENDING
- **Required Actions**: 
