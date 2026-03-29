# Spec Review: Audio Transcription Support

## Summary Table

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | `issue_01` | Missing Properties in `DefaultConfigurations` | [Details](#issue_01-missing-properties-in-defaultconfigurations) | READY |
| High | `issue_02` | Uninitialized Client and Incorrect Model Reference in `SonioxAudioTranscriptionProvider` | [Details](#issue_02-uninitialized-client-and-incorrect-model-reference-in-sonioxaudiotranscriptionprovider) | READY |
| High | `issue_03` | Missing `set_token_tracker` Definition on Provider Architecture | [Details](#issue_03-missing-set_token_tracker-definition-on-provider-architecture) | READY |
| Medium | `issue_04` | Missing Logic in `resolve_model_config` Body | [Details](#issue_04-missing-logic-in-resolve_model_config-body) | READY |
| Medium | `issue_05` | Missed array update in `EditPage.js` `useEffect` Loop | [Details](#issue_05-missed-array-update-in-editpagejs-useeffect-loop) | READY |

---

## Detailed Findings

### `issue_01`: Missing Properties in `DefaultConfigurations`
**Priority:** High
**Status:** READY
**Detailed Description:** The spec establishes new environment variable defaults (`os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")` and `float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`), but fails to instruct adding these specific properties to the `DefaultConfigurations` class in `config_models.py`. The spec only adds `model_provider_name_audio_transcription`. Without expanding the `DefaultConfigurations` class to encompass the model and temperature attributes, `get_bot_defaults()` will throw an `AttributeError` when attempting to build the initial configuration structure for new bots.
**Required Actions:** Update `config_models.py` to explicitly add `model_audio_transcription: str = os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")` and `model_audio_transcription_temperature: float = float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))` inside the `DefaultConfigurations` class to ensure safe template initialization via `get_bot_defaults()`.

### `issue_02`: Uninitialized Client and Incorrect Model Reference in `SonioxAudioTranscriptionProvider`
**Priority:** High
**Status:** READY
**Detailed Description:** The provided code snippet for `SonioxAudioTranscriptionProvider` in the "Provider Architecture" section contains two immediate execution failures:
1. It uses an undefined `client` variable to call `client.stt.transcribe(...)`. The client requires instantiation inside the transcription method or constructor using the resolved API key (e.g., `client = AsyncSonioxClient(api_key=self._resolve_api_key())`).
2. It attempts to access the model configuration via `model=self.settings.model`. In the provided `BaseModelProvider` inheritance tree, the correct path is `model=self.config.provider_config.model`.
**Required Actions:** Update the spec snippet to explicitly instantiate the client at the top of the `transcribe_audio` method using `client = AsyncSonioxClient(api_key=self._resolve_api_key())`, and correct the model reference to `self.config.provider_config.model` inside the `.transcribe(...)` call. This cleanly scopes the client handling and dodges any potential async issues in the constructor.

### `issue_03`: Missing `set_token_tracker` Definition on Provider Architecture
**Priority:** High
**Status:** READY
**Detailed Description:** The spec snippet in `services/model_factory.py` calls `provider.set_token_tracker(token_tracker)` dynamically. However, since the `AudioTranscriptionProvider` branch does not integrate natively with LangChain callbacks (unlike `ChatCompletionProvider`), it manually handles the tracker via an `if self._token_tracker:` check. Neither `_token_tracker` nor `set_token_tracker` are formally defined in the base `AudioTranscriptionProvider` (or `BaseModelProvider`) class. This will result in an `AttributeError: ... has no attribute 'set_token_tracker'` crashing the factory resolution. 
**Required Actions:** Update the spec to formally declare an `__init__` constructor inside the abstract `AudioTranscriptionProvider` class that invokes `super().__init__(config)` and subsequently sets `self._token_tracker = None`. Additionally, append the explicit `def set_token_tracker(self, tracker_func): self._token_tracker = tracker_func` method to this base class to strictly enforce the type-safe behavior requested by the factory integration.

### `issue_04`: Missing Logic in `resolve_model_config` Body
**Priority:** Medium
**Status:** READY
**Detailed Description:** The spec correctly instructs adding the overloaded type hint `Literal["audio_transcription"]` to `resolve_model_config` in `services/resolver.py`. However, it completely omits the instruction to update the actual functional python body logic. Without adding a specific block for this new tier, the code will fall through to the final `else:` block and erroneously attempt to cast the configuration into a `ChatCompletionProviderConfig`, immediately crashing the resolution process.
**Required Actions:** Update the spec to instruct refactoring `resolve_model_config` away from hardcoded `if/elif` statements and instead use a dictionary-based registry mapping (`ConfigTier` -> Pydantic Models) inside the function. The config class should be fetched dynamically using `.get(config_tier, ChatCompletionProviderConfig)` to cleanly support future extensions, including evaluating the `AudioTranscriptionProviderConfig`.

### `issue_05`: Missed array update in `EditPage.js` `useEffect` Loop
**Priority:** Medium
**Status:** READY
**Detailed Description:** The spec asserts: *"Manually append "audio_transcription" to the two hardcoded tier arrays inside the handleFormChange loops for validation."* However, there is actually a **third** occurrence of this hardcoded list `['high', 'low', 'image_moderation', 'image_transcription']` inside the frontend `EditPage.js` file, located within the `useEffect` hook used for data fetching/initialization. Omitting `audio_transcription` from this array mapping will result in missing UI field defaults (such as `api_key_source`) on initial page loads.
**Required Actions:** Update the spec to explicitly mandate finding the third array located inside the `useEffect` data fetching block (around line 135) and appending `"audio_transcription"` to it, alongside the two array modifications already stated for `handleFormChange`.
