# Code Review: LLM Quota Implementation

**Date:** 2026-02-18
**Reviewer:** Sir Gravitush
**Scope:** `docs/llm_quota_spec.md` vs. Implementation

## Executive Summary
The implementation establishes the core infrastructure for LLM quotas but has **three critical deficiencies** that must be addressed before deployment. The most significant issues are the lack of visual feedback for admins (UI), a potential race condition in quota tracking (Backend), and the complete absence of cached token support (Logic), which will lead to incorrect billing.

---

## 1. 🔴 User List UI: Missing Quota Column
**Severity: High**
**Location:** `frontend/src/pages/UserListPage.js`

### Finding
The specification explicitly requires:
> "the grid will have a new column named **Quota Utilization**... new column will show percentage used".

The implementation **did not modify** the User List page. Admins currently have no way to view quota usage across users without manually opening each profile.

### Recommendation
*   Update `frontend/src/pages/UserListPage.js` to add a column header "Quota".
*   In the row render, calculate percentage: `(llm_quota.dollars_used / llm_quota.dollars_per_period) * 100`.
*   Display as a progress bar or percentage text (e.g. "45%").

---

## 2. 🟠 Backend: Quota Update Race Condition
**Severity: Medium**
**Location:** `services/quota_service.py`, method `update_user_usage`

### Finding
The current implementation performs a "read-modify-write" operation in application code:
```python
# 1. READ
user = await self.credentials_collection.find_one(...)
# 2. MODIFY
new_usage = quota.get("dollars_used", 0.0) + cost
# 3. WRITE
await self.credentials_collection.update_one(..., {"$set": {"llm_quota.dollars_used": new_usage}})
```

If a user has multiple bots active, or multiple features consuming tokens simultaneously (e.g., triggered by a group chat event), two processes might read the same `dollars_used` start value, adds their cost, and overwrite each other. This results in **under-counting** usage.

### Recommendation
Use MongoDB's atomic `$inc` operator.
```python
# Atomic update
await self.credentials_collection.update_one(
    {"user_id": user_id},
    {"$inc": {"llm_quota.dollars_used": cost}}
)
```
*Note: You will still need to check if the new total exceeds the limit. You can do this by using `find_one_and_update` to get the returned new document, or by checking after the increment.*

---

## 3. 🔴 Token Tracking: Missing Cached Token Support
**Severity: Critical**
**Location:** `services/tracked_llm.py` and `services/token_consumption_service.py`

### Finding
The specification defines a separate price for `cached_input_tokens` (e.g. $0.125/1M vs $1.25/1M).
The current implementation **ignores cached tokens entirely**.

1.  **Data Source (`tracked_llm.py`)**: The `TokenTrackingCallback` only extracts `input_tokens` and `output_tokens`. It does not look for `prompt_tokens_details` (OpenAI specific) or `usage_metadata` cached fields.
2.  **Data Persistence (`token_consumption_service.py`)**: The `record_event` method signature does not accept `cached_input_tokens`, and the MongoDB schema does not store it.
3.  **Cost Calculation (`quota_service.py`)**: The calculator assumes all input tokens are standard `input_tokens`.

**Impact**:
Since standard `input_tokens` (prompt_tokens) usually include cached tokens in their total count (for OpenAI), and the system charges them at the "High" rate, users will be **overcharged** significantly for cached workloads.

### Recommendation
A complete end-to-end update is required:

1.  **Update `TokenTrackingCallback`**:
    *   Extract `prompt_tokens_details.cached_tokens` from `response.llm_output`.
    *   Subtract this from `prompt_tokens` to get `uncached_input_tokens` (if the API reports total).
2.  **Update `TokenConsumptionService`**:
    *   Add `cached_input_tokens` parameter to `record_event`.
    *   Store `cached_input_tokens` in `token_consumption_events` collection.
3.  **Update `QuotaService`**:
    *   Update `calculate_cost` to accept `cached_input_tokens`.
    *   Formula: `(uncached * rate_input) + (cached * rate_cached) + (output * rate_output)`.
