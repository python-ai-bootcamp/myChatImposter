# Image Transcription Support — Rollout Verification Checklist

**Feature:** `imageTranscriptSupport`  
**Implementation Task:** T52

---

## Deployment Order (CRITICAL)

> [!CAUTION]
> During the migration window, `GET /{bot_id}` calls for un-migrated bots will return **500 errors**
> because `model_validate` raises `ValidationError` for the missing required `image_transcription` field.
> This is accepted behavior — the API is not expected to work until migrations complete.

### Step-by-step deployment sequence:

1. **Stop the application** (or schedule downtime window)
2. **Run migration: backfill bot configs**
   ```bash
   python scripts/migrations/add_image_transcription_tier.py
   ```
   This script:
   - Adds `image_transcription` tier to all existing bot configs
   - Updates the `token_menu` with `image_transcription` pricing
   - Deletes `_mediaProcessorDefinitions` for GIF pool re-seed
3. **Deploy the new code**
4. **Start the application** — pool definitions re-seed automatically from Python defaults (now including `image/gif`)
5. **Run verification checks** (see below)

---

## Pre-Migration Capture

Before running any migration, record baseline counts:

```javascript
// MongoDB shell
db.bot_configurations.countDocuments({})
db.global_configurations.countDocuments({})
db.global_configurations.findOne({ _id: "token_menu" })
db.global_configurations.findOne({ _id: "_mediaProcessorDefinitions" })
```

---

## Post-Migration Verification

### 1. Bot Configuration Backfill
```javascript
// All bots should now have image_transcription
db.bot_configurations.countDocuments({
  "config_data.configurations.llm_configs.image_transcription": { $exists: true }
})
// Should equal total bot count

// Spot-check a sample bot
db.bot_configurations.findOne(
  {},
  { "config_data.configurations.llm_configs.image_transcription": 1 }
)
// Expected: { provider_name: "openAiImageTranscription", provider_config: { model: "gpt-5-mini", ... } }
```

### 2. Token Menu Validation
```javascript
db.global_configurations.findOne({ _id: "token_menu" })
```

Expected structure (3 billable tiers):
| Tier | input_tokens | cached_input_tokens | output_tokens |
|------|-------------|-------------------|--------------|
| `high` | 1.25 | 0.125 | 10 |
| `low` | 0.25 | 0.025 | 2 |
| `image_transcription` | 0.25 | 0.025 | 2 |

> Note: `image_moderation` is intentionally absent — it has no token-cost billing.

### 3. Pool Definitions Re-seed
```javascript
// Should have been deleted by migration, re-created on boot
db.global_configurations.findOne({ _id: "_mediaProcessorDefinitions" })
```

Verify the `ImageVisionProcessor` entry now includes `image/gif`:
```
mimeTypes: ["image/jpeg", "image/png", "image/webp", "image/gif"]
```

### 4. API Smoke Tests
```bash
# Schema endpoint should include image_transcription tier
curl -s http://localhost:8000/api/internal/bots/schema | python -m json.tool | grep image_transcription

# Defaults endpoint should include image_transcription
curl -s http://localhost:8000/api/internal/bots/defaults | python -m json.tool | grep image_transcription

# Tiers endpoint should return all 4 tiers
curl -s http://localhost:8000/api/internal/bots/tiers

# Bot load should NOT 500 (confirms migration ran successfully)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/internal/bots/{any_bot_id}
# Expected: 200
```

### 5. Environment Variables
Confirm these are set (or defaults are acceptable):
- `OPENAI_API_KEY` — required for transcription
- `DEFAULT_MODEL_IMAGE_TRANSCRIPTION` — defaults to `gpt-5-mini`
- `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE` — defaults to `0.05`
- `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT` — defaults to `minimal`

---

## Functional Verification

1. **Send an image** to a bot via WhatsApp/Telegram
2. **Expected flow:** image → moderation check → transcription → formatted output in chat
3. **Verify logs** show:
   - `IMAGE MODERATION ({bot_id}): {moderation_result}`
   - No `IMAGE MODERATION ({bot_id}): Image flagged` (for clean images)
4. **Verify output format:** `[Image Transcription: {description}]\n{caption_if_any}`
5. **Send a GIF** — should now be processed by `ImageVisionProcessor` instead of `UnsupportedMediaProcessor`
