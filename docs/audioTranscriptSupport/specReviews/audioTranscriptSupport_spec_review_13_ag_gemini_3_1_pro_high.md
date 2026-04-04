# Specification Review: audioTranscriptSupport (13_ag_gemini_3_1_pro_high)

## Review Summary

| priority | id                       | title                                                                    | link                                               | status  |
| :------- | :----------------------- | :----------------------------------------------------------------------- | :------------------------------------------------- | :------ |
| High     | ISSUE-ASYNC-LEAK         | `asyncio.create_task` used without a strong reference causes GC leaks    | [#issue-async-leak](#issue-async-leak)             | READY   |
| High     | ISSUE-MISSING-DEPENDENCY | Soniox Python SDK is missing from the Deployment Checklist               | [#issue-missing-dependency](#issue-missing-dependency) | READY   |


<br/>

## Detailed Findings

---

### <a id="issue-async-leak"></a> ISSUE-ASYNC-LEAK: `asyncio.create_task` used without a strong reference causes GC leaks
- **priority:** High
- **id:** ISSUE-ASYNC-LEAK
- **title:** `asyncio.create_task` used without a strong reference causes GC leaks
- **detailed description:** The specification instructs the developer to spawn an asynchronous fire-and-forget closure within the `finally` block utilizing `asyncio.create_task(_cleanup())` in order to safeguard Soniox resource deletion against parent `CancelledError` limits. However, in standard Python 3.9+, standard `create_task()` calls only instantiate a weak reference. During heavy processing periods, if the un-referenced background task hangs temporarily or awaits network closure, it is inherently vulnerable to being spontaneously deleted/destroyed mid-execution by the Python garbage collector. This silently circumvents the entire purpose of the `_cleanup` function, reliably leaking the external API artifacts. 
- **status:** READY
- **required actions:** Introduce a class-level or global `set` (e.g., `_background_tasks = set()`). When spawning the cleanup task, add it to the set (`task = asyncio.create_task(_cleanup())`; `_background_tasks.add(task)`) and attach a done callback to remove it upon completion (`task.add_done_callback(_background_tasks.discard)`). This introduces a strong reference and ensures GC survival.

---

### <a id="issue-missing-dependency"></a> ISSUE-MISSING-DEPENDENCY: Soniox Python SDK is missing from the Deployment Checklist
- **priority:** High
- **id:** ISSUE-MISSING-DEPENDENCY
- **title:** Soniox Python SDK is missing from the Deployment Checklist
- **detailed description:** The 'Technical Details' section enforces adopting the official `AsyncSonioxClient` via the explicit `soniox` library import framework (i.e. `from soniox import AsyncSonioxClient`). Nevertheless, this package is not a preexisting project constituent, and neither the 'Relevant Background Information' nor the 'Deployment Checklist' explicitly directs developers or operations mapping to introduce the `soniox` dependency within the `requirements.txt` environment schema. Failure to include this instruction guarantees systemic `ModuleNotFoundError` crashes upon initial CI/CD release or staging tests.
- **status:** READY
- **required actions:** Update the "Deployment Checklist" section of the specification to include an explicit step directing the developer to append the `soniox` package (preferably pinning the specific tested version) to the root `requirements.txt` file before any deployments.

