# Moderate Image Spec Review (Codex 5.3)

## Findings Table

| priority | id | title | link | status |
|---|---|---|---|---|
| P1 | MIMG-501 | Missing rollout safety for absent/invalid bot moderation config | [Jump](#mimg-501) | PENDING |
| P2 | MIMG-502 | Wording ambiguity: default model vs bot-authoritative config | [Jump](#mimg-502) | PENDING |
| P2 | MIMG-503 | Logging requirement is underspecified for production safety | [Jump](#mimg-503) | PENDING |
| P2 | MIMG-504 | Verification scope is too narrow to protect critical behavior | [Jump](#mimg-504) | PENDING |

---

### MIMG-501
- **priority:** P1
- **id:** MIMG-501
- **title:** Missing rollout safety for absent/invalid bot moderation config
- **status:** PENDING
- **detailed description:**  
  The spec correctly requires resolving moderation provider via `create_model_provider(bot_id, "media_processing", "image_moderation")` and bubbling failures to centralized error handling. However, it does not define rollout prerequisites or acceptance criteria for existing bots that may have missing or invalid `configurations.llm_configs.image_moderation` entries.  
  
  In the current architecture, `resolve_model_config()` throws when the tier is missing or malformed, and `ImageVisionProcessor` is instructed not to catch this. That means image jobs fail immediately and placeholders are resolved as failure content. Without an explicit rollout/migration/preflight requirement in the spec, deployment can silently convert all image messages for affected bots into failures.  
  
  This is a production-impacting gap because it affects runtime behavior at scale and is not just implementation style.

- **selected mitigation / action item:**  
  **E) Explicitly acknowledge and accept the risk in the spec.**  
  Add a short statement to the spec that rollout-safety checks/migrations are intentionally out of scope for this phase because all entities were already upgraded, and the residual probability of occurrence is considered negligible and accepted.  
  Keep this item open until that statement is added to the spec text.

### MIMG-502
- **priority:** P2
- **id:** MIMG-502
- **title:** Wording ambiguity: default model vs bot-authoritative config
- **status:** PENDING
- **detailed description:**  
  The current architecture already supports the intended behavior: `image_moderation` tier resolution selects the moderation provider path, and model choice comes from bot configuration.  
  
  The risk here is primarily wording clarity. The phrase "Use OpenAI moderation model `omni-moderation-latest`" can be misread as a hard runtime lock, while your intended behavior is that `omni-moderation-latest` is a default and individual bots may override to compatible moderation models (for example `omni-moderation-2024-09-26`) through config.

- **selected mitigation / action item:**  
  Clarify the spec text so runtime behavior is unambiguous:
  - `image_moderation` bot configuration is authoritative at runtime.
  - `openAiModeration` and `omni-moderation-latest` are defaults for new/default configs.
  - Implementation must not hardcode model selection in processor logic.

### MIMG-503
- **priority:** P2
- **id:** MIMG-503
- **title:** Logging requirement is underspecified for production safety
- **status:** PENDING
- **detailed description:**  
  The spec mandates:
  - raw SDK response logging in `OpenAiModerationProvider`, and
  - normalized moderation dict logging in `ImageVisionProcessor` using `logger.info`.
  
  The missing part is only explicit policy wording. Your intended behavior is straightforward: log all moderation-related outputs at `INFO` level in this phase.

- **selected mitigation / action item:**  
  Clarify spec logging policy explicitly:
  - Log everything relevant to moderation flow.
  - Use `INFO` level for all these logs in this phase (provider raw SDK response and processor normalized moderation result).
  - Keep this item open until this policy is written in the spec text.

### MIMG-504
- **priority:** P2
- **id:** MIMG-504
- **title:** Verification scope is too narrow to protect critical behavior
- **status:** PENDING
- **detailed description:**  
  Section 1 requires a test/assertion proving `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` points to the new module, which is good. But the spec does not require verification for the highest-risk behavior changes it introduces:
  - async contract migration from `quota_exceeded` to `bot_id` across all processors,
  - event-loop-safe file read/base64 path (`asyncio.to_thread`),
  - updated provider interface (`moderate_image(base64_image, mime_type)`),
  - exact moderation payload shape sent to SDK.
  
  With only factory wiring verification, regressions can pass unnoticed while moderation silently fails at runtime.

- **selected mitigation / action item:**  
  **D) Add a verification checklist in the spec (proof method is flexible).**  
  Require explicit verification evidence for each critical change, but do not force a specific mechanism (unit test, integration test, assertion, or equivalent proof all acceptable):
  - `process_media(..., bot_id)` contract migration is complete.
  - `ImageModerationProvider`/`OpenAiModerationProvider` signature update is applied.
  - image bytes are read and base64-encoded via event-loop-safe path.
  - moderation payload shape matches the required SDK structure.
