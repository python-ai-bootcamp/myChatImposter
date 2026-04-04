# Audio Transcription Support Spec Review

## Review Summary

| priority | id | title | link | status |
| :--- | :--- | :--- | :--- | :--- |
| Medium | ATS-11-01 | Contradictory Soniox Usage Metrics Extraction | [#ats-11-01-contradictory-soniox-usage-metrics-extraction](#ats-11-01-contradictory-soniox-usage-metrics-extraction) | READY |
| Low | ATS-11-02 | Missing `display_media_type` Parameter in `format_processing_result` Signature | [#ats-11-02-missing-display_media_type-parameter-in-format_processing_result-signature](#ats-11-02-missing-display_media_type-parameter-in-format_processing_result-signature) | READY |
| Low | ATS-11-03 | Missing `AudioTranscriptionProvider` Import in Model Factory | [#ats-11-03-missing-audiotranscriptionprovider-import-in-model-factory](#ats-11-03-missing-audiotranscriptionprovider-import-in-model-factory) | READY |
| Low | ATS-11-04 | Inconsistent `feature_name` Usage in `create_model_provider` | [#ats-11-04-inconsistent-feature_name-usage-in-create_model_provider](#ats-11-04-inconsistent-feature_name-usage-in-create_model_provider) | READY |

---

## Detailed Review Items

### ATS-11-01: Contradictory Soniox Usage Metrics Extraction
- **priority**: Medium
- **id**: ATS-11-01
- **title**: Contradictory Soniox Usage Metrics Extraction
- **detailed description**: The narrative text in the "Transcription response normalization contract" explicitly instructs the developer to extract token usage metrics directly via `client.stt.get(transcription.id).usage`. However, the provided reference Python snippet in the technical details explicitly contradicts this directive by asserting: "Note: Soniox does not provide token usage natively." The snippet instead implements an arithmetic calculation based on `audio_duration_ms` and output text length. The specification narrative should be corrected to align perfectly with the snippet's approach to avoid confusion during implementation, confirming whether `.usage` natively exists or if mathematical estimation is the verified path forward.
- **status**: READY
- **required actions**: Update the narrative text in the "Transcription response normalization contract" block to explicitly discard the `.usage` requirement. Instruct the developer to mathematically estimate input and output tokens using `audio_duration_ms` and transcript text length precisely as modeled in the provided reference Python snippet, clarifying that Soniox currently lacks native token usage metrics in its API responses.

### ATS-11-02: Missing `display_media_type` Parameter in `format_processing_result` Signature
- **priority**: Low
- **id**: ATS-11-02
- **title**: Missing `display_media_type` Parameter in `format_processing_result` Signature
- **detailed description**: The specification guides the developer to add an optional `display_media_type` attribute to the `ProcessingResult` dataclass to allow robust processors to override the dynamic capitalization of `mime_type` prefix injections inside `format_processing_result()`. However, `format_processing_result` operates on individual primitive arguments (like `content` and `unprocessable_media`) rather than consuming an existing `ProcessingResult` object instance directly in its signature. To functionally process this override, the specification must explicitly mandate expanding the `format_processing_result` signature to accept an optional `display_media_type: str = None` parameter, and direct `BaseMediaProcessor.process_job()` to pass `result.display_media_type` onto this format call.
- **status**: READY
- **required actions**: Update the specification to explicitly dictate the expansion of the `format_processing_result` function signature to include a new, optional `display_media_type: str = None` parameter. Furthermore, instruct that `BaseMediaProcessor.process_job` must explicitly extract `result.display_media_type` and supply it to the formatter upon call.

### ATS-11-03: Missing `AudioTranscriptionProvider` Import in Model Factory
- **priority**: Low
- **id**: ATS-11-03
- **title**: Missing `AudioTranscriptionProvider` Import in Model Factory
- **detailed description**: The specification carefully instructs the developer to add a polymorphic type evasion branch reading `elif isinstance(provider, AudioTranscriptionProvider): return provider` within the `create_model_provider` factory algorithm, and enforces expanding its return type hints in `services/model_factory.py`. However, it fails to formally direct the developer to add the necessary import statement for `AudioTranscriptionProvider` from the `model_providers.audio_transcription` module. In Python, utilizing `isinstance` on a non-imported class results in an immediate `NameError` crash at runtime. The spec should explicitly mandate this import.
- **status**: READY
- **required actions**: Update the specification to explicitly mandate developers insert the import statement `from model_providers.audio_transcription import AudioTranscriptionProvider` at the top of the `model_factory.py` file to prevent the subsequent runtime `NameError` block branch crash.

### ATS-11-04: Inconsistent `feature_name` Usage in `create_model_provider`
- **priority**: Low
- **id**: ATS-11-04
- **title**: Inconsistent `feature_name` Usage in `create_model_provider`
- **detailed description**: The specification mandates passing the raw string `"audio_transcription"` as the `feature_name` argument to the `create_model_provider()` factory call to accurately attribute tracking metrics. Alternatively, a thorough examination of the codebase reveals that the equivalent preexisting processor sibling, `ImageVisionProcessor`, ubiquitously utilizes `"media_processing"` as its designated tracking feature name for both its moderation loop and its image transcription API calls to `create_model_provider()`. While functionally sound, utilizing `"audio_transcription"` fractures pipeline token metrics attribution. Aligning the implementation with `"media_processing"` optimizes data continuity and organizational coherence.
- **status**: READY
- **required actions**: Add an explicit instruction for the developer to modify the existing `ImageVisionProcessor` implementation to pass `"image_moderation"` and `"image_transcription"` as the `feature_name` values instead of `"media_processing"` when it invokes `create_model_provider()`. This custom mitigation elegantly eliminates the inconsistency by enforcing granular, per-feature token tracking tags across all media processors while permitting the new workflow to correctly use `"audio_transcription"`.
