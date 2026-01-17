// This file contains JavaScript classes that mirror the backend's Pydantic models.
// These classes include validation logic to ensure that the data structure is correct
// before sending it to the backend.

class ValidationError extends Error {
  constructor(message, path) {
    super(message);
    this.name = 'ValidationError';
    this.path = path;
  }
}

class ChatProviderSettings {
  constructor({ allow_group_messages = false, process_offline_messages = false, ...extra }) {
    this.allow_group_messages = allow_group_messages;
    this.process_offline_messages = process_offline_messages;
    // Allow extra fields
    Object.assign(this, extra);
  }

  static validate(data) {
    if (typeof data.allow_group_messages !== 'boolean') {
      throw new ValidationError('allow_group_messages must be a boolean.', 'configurations.chat_provider_config.provider_config.allow_group_messages');
    }
    if (typeof data.process_offline_messages !== 'boolean') {
      throw new ValidationError('process_offline_messages must be a boolean.', 'configurations.chat_provider_config.provider_config.process_offline_messages');
    }
    return new ChatProviderSettings(data);
  }
}

class ChatProviderConfig {
  constructor({ provider_name, provider_config }) {
    this.provider_name = provider_name;
    this.provider_config = new ChatProviderSettings(provider_config);
  }

  static validate(data) {
    if (!data.provider_name || typeof data.provider_name !== 'string') {
      throw new ValidationError('provider_name is required and must be a string.', 'configurations.chat_provider_config.provider_name');
    }
    if (!data.provider_config || typeof data.provider_config !== 'object') {
      throw new ValidationError('provider_config is required.', 'configurations.chat_provider_config.provider_config');
    }
    ChatProviderSettings.validate(data.provider_config);
    return new ChatProviderConfig(data);
  }
}

class QueueConfig {
  constructor({ max_messages = 10, max_characters = 1000, max_days = 1, max_characters_single_message = 300 }) {
    this.max_messages = max_messages;
    this.max_characters = max_characters;
    this.max_days = max_days;
    this.max_characters_single_message = max_characters_single_message;
  }

  static validate(data) {
    if (typeof data.max_messages !== 'number') {
      throw new ValidationError('max_messages must be a number.', 'configurations.queue_config.max_messages');
    }
    if (typeof data.max_characters !== 'number') {
      throw new ValidationError('max_characters must be a number.', 'configurations.queue_config.max_characters');
    }
    if (typeof data.max_days !== 'number') {
      throw new ValidationError('max_days must be a number.', 'configurations.queue_config.max_days');
    }
    if (typeof data.max_characters_single_message !== 'number') {
      throw new ValidationError('max_characters_single_message must be a number.', 'configurations.queue_config.max_characters_single_message');
    }
    return new QueueConfig(data);
  }
}

class LLMProviderSettings {
  constructor({ api_key = null, model, temperature = 0.7, record_llm_interactions = false, ...extra }) {
    this.api_key = api_key;
    this.model = model;
    this.temperature = temperature;
    this.record_llm_interactions = record_llm_interactions;
    // Allow extra fields
    Object.assign(this, extra);
  }

  static validate(data) {
    if (data.api_key !== null && typeof data.api_key !== 'string') {
      throw new ValidationError('api_key must be a string or null.', 'configurations.llm_provider_config.provider_config.api_key');
    }
    if (!data.model || typeof data.model !== 'string') {
      throw new ValidationError('model is required and must be a string.', 'configurations.llm_provider_config.provider_config.model');
    }
    if (typeof data.temperature !== 'number') {
      throw new ValidationError('temperature must be a number.', 'configurations.llm_provider_config.provider_config.temperature');
    }
    if (data.record_llm_interactions !== undefined && typeof data.record_llm_interactions !== 'boolean') {
      throw new ValidationError('record_llm_interactions must be a boolean.', 'configurations.llm_provider_config.provider_config.record_llm_interactions');
    }
    return new LLMProviderSettings(data);
  }
}

class LLMProviderConfig {
  constructor({ provider_name, provider_config }) {
    this.provider_name = provider_name;
    this.provider_config = new LLMProviderSettings(provider_config);
  }

  static validate(data) {
    if (!data.provider_name || typeof data.provider_name !== 'string') {
      throw new ValidationError('provider_name is required and must be a string.', 'configurations.llm_provider_config.provider_name');
    }
    if (!data.provider_config || typeof data.provider_config !== 'object') {
      throw new ValidationError('provider_config is required.', 'configurations.llm_provider_config.provider_config');
    }
    LLMProviderSettings.validate(data.provider_config);
    return new LLMProviderConfig(data);
  }
}

// Feature Classes
class AutomaticBotReplyFeature {
  constructor({ enabled = false, respond_to_whitelist = [], respond_to_whitelist_group = [], chat_system_prompt = '' }) {
    this.enabled = enabled;
    this.respond_to_whitelist = respond_to_whitelist;
    this.respond_to_whitelist_group = respond_to_whitelist_group;
    this.chat_system_prompt = chat_system_prompt;
  }

  static validate(data) {
    if (typeof data.enabled !== 'boolean') {
      throw new ValidationError('enabled must be a boolean.', 'features.automatic_bot_reply.enabled');
    }
    if (!Array.isArray(data.respond_to_whitelist)) {
      throw new ValidationError('respond_to_whitelist must be an array.', 'features.automatic_bot_reply.respond_to_whitelist');
    }
    if (!Array.isArray(data.respond_to_whitelist_group)) {
      throw new ValidationError('respond_to_whitelist_group must be an array.', 'features.automatic_bot_reply.respond_to_whitelist_group');
    }
    if (data.chat_system_prompt !== undefined && typeof data.chat_system_prompt !== 'string') {
      throw new ValidationError('chat_system_prompt must be a string.', 'features.automatic_bot_reply.chat_system_prompt');
    }
    return new AutomaticBotReplyFeature(data);
  }
}

class PeriodicGroupTrackingFeature {
  constructor({ enabled = false, tracked_groups = [] }) {
    this.enabled = enabled;
    this.tracked_groups = tracked_groups;
  }

  static validate(data) {
    if (typeof data.enabled !== 'boolean') {
      throw new ValidationError('enabled must be a boolean.', 'features.periodic_group_tracking.enabled');
    }
    if (!Array.isArray(data.tracked_groups)) {
      throw new ValidationError('tracked_groups must be an array.', 'features.periodic_group_tracking.tracked_groups');
    }
    return new PeriodicGroupTrackingFeature(data);
  }
}

class KidPhoneSafetyTrackingFeature {
  constructor({ enabled = false }) {
    this.enabled = enabled;
  }

  static validate(data) {
    if (typeof data.enabled !== 'boolean') {
      throw new ValidationError('enabled must be a boolean.', 'features.kid_phone_safety_tracking.enabled');
    }
    return new KidPhoneSafetyTrackingFeature(data);
  }
}

class FeaturesConfiguration {
  constructor({ automatic_bot_reply, periodic_group_tracking, kid_phone_safety_tracking }) {
    this.automatic_bot_reply = new AutomaticBotReplyFeature(automatic_bot_reply || {});
    this.periodic_group_tracking = new PeriodicGroupTrackingFeature(periodic_group_tracking || {});
    this.kid_phone_safety_tracking = new KidPhoneSafetyTrackingFeature(kid_phone_safety_tracking || {});
  }

  static validate(data) {
    if (data.automatic_bot_reply) {
      AutomaticBotReplyFeature.validate(data.automatic_bot_reply);
    }
    if (data.periodic_group_tracking) {
      PeriodicGroupTrackingFeature.validate(data.periodic_group_tracking);
    }
    if (data.kid_phone_safety_tracking) {
      KidPhoneSafetyTrackingFeature.validate(data.kid_phone_safety_tracking);
    }
    return new FeaturesConfiguration(data);
  }
}

class UserDetails {
  constructor({ first_name = '', last_name = '', timezone = 'UTC', language_code = 'en' }) {
    this.first_name = first_name;
    this.last_name = last_name;
    this.timezone = timezone;
    this.language_code = language_code;
  }

  static validate(data) {
    if (data.first_name !== undefined && typeof data.first_name !== 'string') {
      throw new ValidationError('first_name must be a string.', 'configurations.user_details.first_name');
    }
    if (data.last_name !== undefined && typeof data.last_name !== 'string') {
      throw new ValidationError('last_name must be a string.', 'configurations.user_details.last_name');
    }
    if (data.timezone !== undefined && typeof data.timezone !== 'string') {
      throw new ValidationError('timezone must be a string.', 'configurations.user_details.timezone');
    }
    if (data.language_code !== undefined && typeof data.language_code !== 'string') {
      throw new ValidationError('language_code must be a string.', 'configurations.user_details.language_code');
    }
    return new UserDetails(data);
  }
}

class ConfigurationsSettings {
  constructor({ user_details, chat_provider_config, queue_config, context_config, llm_provider_config }) {
    this.user_details = new UserDetails(user_details || {});
    this.chat_provider_config = new ChatProviderConfig(chat_provider_config);
    this.queue_config = new QueueConfig(queue_config || {});
    this.context_config = context_config || {};
    this.llm_provider_config = new LLMProviderConfig(llm_provider_config);
  }

  static validate(data) {
    if (data.user_details && typeof data.user_details === 'object') {
      UserDetails.validate(data.user_details);
    }

    if (!data.chat_provider_config || typeof data.chat_provider_config !== 'object') {
      throw new ValidationError('chat_provider_config is required.', 'configurations.chat_provider_config');
    }
    ChatProviderConfig.validate(data.chat_provider_config);

    if (data.queue_config && typeof data.queue_config === 'object') {
      QueueConfig.validate(data.queue_config);
    }

    if (!data.llm_provider_config || typeof data.llm_provider_config !== 'object') {
      throw new ValidationError('llm_provider_config is required.', 'configurations.llm_provider_config');
    }
    LLMProviderConfig.validate(data.llm_provider_config);

    return new ConfigurationsSettings(data);
  }
}

class UserConfiguration {
  constructor({ user_id, configurations, features }) {
    this.user_id = user_id;
    this.configurations = new ConfigurationsSettings(configurations || {});
    this.features = new FeaturesConfiguration(features || {});
  }

  static validate(data) {
    if (!data.user_id || typeof data.user_id !== 'string') {
      throw new ValidationError('user_id is required and must be a string.', 'user_id');
    }

    if (!data.configurations || typeof data.configurations !== 'object') {
      throw new ValidationError('configurations is required.', 'configurations');
    }
    ConfigurationsSettings.validate(data.configurations);

    if (data.features && typeof data.features === 'object') {
      FeaturesConfiguration.validate(data.features);
    }

    return new UserConfiguration(data);
  }
}

export function validateConfiguration(config) {
  try {
    if (Array.isArray(config)) {
      config.forEach(UserConfiguration.validate);
    } else {
      UserConfiguration.validate(config);
    }
    return { isValid: true, errors: [] };
  } catch (error) {
    if (error instanceof ValidationError) {
      return { isValid: false, errors: [{ path: error.path, message: error.message }] };
    }
    // For unexpected errors
    return { isValid: false, errors: [{ path: 'general', message: 'An unexpected error occurred during validation.' }] };
  }
}
