 [NBPD]- video moderation
 [NBPD]- video transcript

 - reduce api cost by switching to gemini 2.0 flash or gemini 2.0 flash lite
 [NBPD]- kid safety feature
 - add more stuf to central services/resolver.py and make more existing code consume its services
 - make services/resolver.py more efficient by utilizing caches and cache invalidations on bot config changes
 [NBPD]- create client cache (bot_id, config_tier, feature_name)-> long living client
 - `llm_configs` → `model_provider_configs` (full blast radius will be required to be addressed including upgrade scripts, UI changes, model changes, reference changes etc.)
 - unify infrastructure\models.py which was added seperately for media workers with previously existed config_models.py
[NBPD] - convey inactive bots due to user token quota depleted ("user_enabled": false) in the dashboard UI
[NBPD] - proper fresh schema deployment and upgrade strategy
 - fix doc pages internal/external issues

 [NBPD]=needed before production deploymet