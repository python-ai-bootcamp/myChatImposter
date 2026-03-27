# Spec Review: Audio Transcription Support

## Summary Table

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | `issue_01` | Missing Properties in `DefaultConfigurations` | [Details](#issue_01-missing-properties-in-defaultconfigurations) | PENDING |
| High | `issue_02` | Uninitialized Client and Incorrect Model Reference in `SonioxAudioTranscriptionProvider` | [Details](#issue_02-uninitialized-client-and-incorrect-model-reference-in-sonioxaudiotranscriptionprovider) | PENDING |
| High | `issue_03` | Missing `set_token_tracker` Definition on Provider Architecture | [Details](#issue_03-missing-set_token_tracker-definition-on-provider-architecture) | PENDING |
| Medium | `issue_04` | Missing Logic in `resolve_model_config` Body | [Details](#issue_04-missing-logic-in-resolve_model_config-body) | PENDING |
| Medium | `issue_05` | Missed array update in `EditPage.js` `useEffect` Loop | [Details](#issue_05-missed-array-update-in-editpagejs-useeffect-loop) | PENDING |

---

## Detailed Findings

### `issue_01`: Missing Properties in `DefaultConfigurations`
**Priority:** High
**Status:** PENDING
**Detailed Description:** The spec establishes new environment variable defaults (`os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")` and `float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`), but fails to instruct adding these specific properties to the `DefaultConfigurations` class in `config_models.py`. The spec only adds `model_provider_name_audio_transcription`. Without expanding the `DefaultConfigurations` class to encompass the model and temperature attributes, `get_bot_defaults()` will throw an `AttributeError` when attempting to build the initial configuration structure for new bots.
**Required Actions:** 

### `issue_02`: Uninitialized Client and Incorrect Model Reference in `SonioxAudioTranscriptionProvider`
**Priority:** High
**Status:** PENDING
**Detailed Description:** The provided code snippet for `SonioxAudioTranscriptionProvider` in the "Provider Architecture" section contains two immediate execution failures:
1. It uses an undefined `client` variable to call `client.stt.transcribe(...)`. The client requires instantiation inside the transcription method or constructor using the resolved API key (e.g., `client = AsyncSonioxClient(api_key=self._resolve_api_key())`).
2. It attempts to access the model configuration via `model=self.settings.model`. In the provided `BaseModelProvider` inheritance tree, the correct path is `model=self.config.provider_config.model`.
**Required Actions:** 

### `issue_03`: Missing `set_token_tracker` Definition on Provider Architecture
**Priority:** High
**Status:** PENDING
**Detailed Description:** The spec snippet in `services/model_factory.py` calls `provider.set_token_tracker(token_tracker)` dynamically. However, since the `AudioTranscriptionProvider` branch does not integrate natively with LangChain callbacks (unlike `ChatCompletionProvider`), it manually handles the tracker via an `if self._token_tracker:` check. Neither `_token_tracker` nor `set_token_tracker` are formally defined in the base `AudioTranscriptionProvider` (or `BaseModelProvider`) class. This will result in an `AttributeError: ... has no attribute 'set_token_tracker'` crashing the factory resolution. 
**Required Actions:** 

### `issue_04`: Missing Logic in `resolve_model_config` Body
**Priority:** Medium
**Status:** PENDING
**Detailed Description:** The spec states: *"services/resolver.py: Add the overloaded type Literal["audio_transcription"] to resolve_model_config."* While this correctly sets the type hints, it completely overlooks updating the actual functional body of `resolve_model_config`. Thus, when executing, the `config_tier == "audio_transcription"` condition will fall through to the final block and erroneously attempt to return a `ChatCompletionProviderConfig.model_validate(tier_data)` instead of the required `AudioTranscriptionProviderConfig`.
**Required Actions:** 

### `issue_05`: Missed array update in `EditPage.js` `useEffect` Loop
**Priority:** Medium
**Status:** PENDING
**Detailed Description:** The spec asserts: *"Manually append "audio_transcription" to the two hardcoded tier arrays inside the handleFormChange loops for validation."* However, there is actually a **third** occurrence of this hardcoded list `['high', 'low', 'image_moderation', 'image_transcription']` inside the frontend `EditPage.js` file, located within the `useEffect` hook used for data fetching/initialization. Omitting `audio_transcription` from this array mapping will result in missing UI field defaults (such as `api_key_source`) on initial page loads.
**Required Actions:** 
