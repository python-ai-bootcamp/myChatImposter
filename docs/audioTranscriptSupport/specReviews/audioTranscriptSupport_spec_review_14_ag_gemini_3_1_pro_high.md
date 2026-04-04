## Audio Transcription Support: Spec Review `14_ag_gemini_3_1_pro_high`

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | test_format_processing_result_signature_crash | Missing test updates for `format_processing_result` signature change | [Issue Details](#test_format_processing_result_signature_crash) | READY |
| High | test_import_error_stub_processor | `ImportError` crash in test file due to removed stub processor | [Issue Details](#test_import_error_stub_processor) | READY |

---

### Detailed Descriptions

#### test_format_processing_result_signature_crash
* **Priority:** High
* **Status:** READY
* **Required Actions:** Add an explicit instruction to the spec's `Test Expectations` section directing the developer to update the four `format_processing_result` test fixtures in `tests/test_image_transcription_support.py` by providing a dummy string for the new `mime_type` parameter (e.g., `mime_type="image/jpeg"`).
* **Description:** The specification instructs a refactoring of `format_processing_result` in `media_processors/base.py` to declare a **required** `mime_type: str` parameter. While it correctly lists updates to call sites within the main `BaseMediaProcessor` class, it completely misses the unit tests in `tests/test_image_transcription_support.py`. This test file directly invokes `format_processing_result` four independent times across its test fixtures (e.g., `test_format_processing_result_basic`, `test_format_processing_result_with_filename`). Implementing the spec as written without updating these tests to pass a mock `mime_type` string will break the CI pipeline due to `TypeError: format_processing_result() missing 1 required positional argument: 'mime_type'` crashes.

#### test_import_error_stub_processor
* **Priority:** High
* **Status:** READY
* **Required Actions:** Explicitly instruct the developer to completely remove the `AudioTranscriptionProcessor` import and its associated signature checks from `tests/test_image_transcription_support.py`, and instead implement those verification assertions inside a newly created, dedicated `test_audio_transcription_support.py` unit test file.
* **Description:** The specification details moving `AudioTranscriptionProcessor` out of `media_processors/stub_processors.py` into a new distinct file (`audio_transcription_processor.py`), explicitly requiring the developer to delete the old stub. However, `tests/test_image_transcription_support.py` explicitly imports `AudioTranscriptionProcessor` from `media_processors.stub_processors` (around line 32) to assert its `process_media` signature inside `test_process_media_no_caption_parameter`. Deleting the stub as specified without instructing the developer to update this import path will result in an immediate `ImportError: cannot import name 'AudioTranscriptionProcessor' from 'media_processors.stub_processors'` when the test suite runs.
