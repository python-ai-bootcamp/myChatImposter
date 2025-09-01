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
      throw new ValidationError('allow_group_messages must be a boolean.', 'chat_provider_config.provider_config.allow_group_messages');
    }
    if (typeof data.process_offline_messages !== 'boolean') {
      throw new ValidationError('process_offline_messages must be a boolean.', 'chat_provider_config.provider_config.process_offline_messages');
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
      throw new ValidationError('provider_name is required and must be a string.', 'chat_provider_config.provider_name');
    }
    if (!data.provider_config || typeof data.provider_config !== 'object') {
      throw new ValidationError('provider_config is required.', 'chat_provider_config.provider_config');
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
      throw new ValidationError('max_messages must be a number.', 'queue_config.max_messages');
    }
    if (typeof data.max_characters !== 'number') {
      throw new ValidationError('max_characters must be a number.', 'queue_config.max_characters');
    }
    if (typeof data.max_days !== 'number') {
      throw new ValidationError('max_days must be a number.', 'queue_config.max_days');
    }
    if (typeof data.max_characters_single_message !== 'number') {
      throw new ValidationError('max_characters_single_message must be a number.', 'queue_config.max_characters_single_message');
    }
    return new QueueConfig(data);
  }
}

class LLMProviderSettings {
  constructor({ api_key = null, model, temperature = 0.7, system = "", ...extra }) {
    this.api_key = api_key;
    this.model = model;
    this.temperature = temperature;
    this.system = system;
    // Allow extra fields
    Object.assign(this, extra);
  }

  static validate(data) {
    if (data.api_key !== null && typeof data.api_key !== 'string') {
      throw new ValidationError('api_key must be a string or null.', 'llm_provider_config.provider_config.api_key');
    }
    if (!data.model || typeof data.model !== 'string') {
      throw new ValidationError('model is required and must be a string.', 'llm_provider_config.provider_config.model');
    }
    if (typeof data.temperature !== 'number') {
      throw new ValidationError('temperature must be a number.', 'llm_provider_config.provider_config.temperature');
    }
    if (typeof data.system !== 'string') {
      throw new ValidationError('system must be a string.', 'llm_provider_config.provider_config.system');
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
      throw new ValidationError('provider_name is required and must be a string.', 'llm_provider_config.provider_name');
    }
    if (!data.provider_config || typeof data.provider_config !== 'object') {
      throw new ValidationError('provider_config is required.', 'llm_provider_config.provider_config');
    }
    LLMProviderSettings.validate(data.provider_config);
    return new LLMProviderConfig(data);
  }
}

class UserConfiguration {
  constructor({ user_id, respond_to_whitelist = [], chat_provider_config, queue_config, llm_provider_config = null }) {
    this.user_id = user_id;
    this.respond_to_whitelist = respond_to_whitelist;
    this.chat_provider_config = new ChatProviderConfig(chat_provider_config);
    this.queue_config = new QueueConfig(queue_config);
    if (llm_provider_config) {
      this.llm_provider_config = new LLMProviderConfig(llm_provider_config);
    } else {
      this.llm_provider_config = null;
    }
  }

  static validate(data) {
    if (!data.user_id || typeof data.user_id !== 'string') {
      throw new ValidationError('user_id is required and must be a string.', 'user_id');
    }
    if (!Array.isArray(data.respond_to_whitelist)) {
      throw new ValidationError('respond_to_whitelist must be an array.', 'respond_to_whitelist');
    }
    if (!data.chat_provider_config || typeof data.chat_provider_config !== 'object') {
      throw new ValidationError('chat_provider_config is required.', 'chat_provider_config');
    }
    ChatProviderConfig.validate(data.chat_provider_config);

    if (!data.queue_config || typeof data.queue_config !== 'object') {
      throw new ValidationError('queue_config is required.', 'queue_config');
    }
    QueueConfig.validate(data.queue_config);

    if (data.llm_provider_config !== null && (typeof data.llm_provider_config !== 'object' || data.llm_provider_config === undefined)) {
        throw new ValidationError('llm_provider_config must be an object or null.', 'llm_provider_config');
    }

    if (data.llm_provider_config) {
      LLMProviderConfig.validate(data.llm_provider_config);
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
