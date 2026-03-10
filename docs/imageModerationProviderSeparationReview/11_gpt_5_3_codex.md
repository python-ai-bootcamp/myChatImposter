# Review: Image Moderation Provider Separation Specification

**Reviewer**: GPT-5.3 Codex  
**Date**: 2026-03-10  
**Spec File**: `docs/imageModerationProviderSeparation.md`  
**Codebase Snapshot**: Current working tree (pre-implementation)

---

## Summary Table

| Priority | ID | Title | Link | Status |
|---|---|---|---|---|
| - | NONE | No substantial pre-implementation issues found | [Details](#overall-assessment) | done |

---

## Detailed Findings

No serious findings were identified that should block implementation.

I re-checked the currently impacted areas described in the prompt and spec, including:
- provider base/factory flow (`services/llm_factory.py`, `services/tracked_llm.py`, `llm_providers/*`)
- async initialization call paths (`features/automatic_bot_reply/service.py`, `services/bot_lifecycle_service.py`, `routers/bot_management.py`)
- periodic tracking cascade (`features/periodic_group_tracking/service.py`, `runner.py`, `extractor.py`)
- config/schema/defaults surface (`config_models.py`, `routers/bot_management.py`, `routers/bot_ui.py`)
- token/quota typing impacts (`services/token_consumption_service.py`, `services/quota_service.py`)
- provider discovery utility (`utils/provider_utils.py`)

Given the current spec content, the previously risky gaps (import migration coverage, async cascade duplication, cron owner threading consistency, and schema patch key migration) are already addressed in this revision.

---

<a id="overall-assessment"></a>
## Overall Assessment

The spec is solid enough to start implementation.

Recommended implementation guardrails:
1. keep the migration script mandatory (especially `image_moderation.provider_name -> openAiModeration`);
2. run a full import/type sweep immediately after package rename (`llm_providers` -> `model_providers`);
3. run targeted tests for `automatic_bot_reply`, `periodic_group_tracking`, and token-flow integration before merge.

