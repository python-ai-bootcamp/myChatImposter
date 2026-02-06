
import { validateConfiguration } from './configModels';

describe('validateConfiguration', () => {

    const validConfig = {
        bot_id: 'test-bot',
        configurations: {
            user_details: {
                first_name: 'Test',
                last_name: 'User',
                timezone: 'UTC',
                language_code: 'en'
            },
            chat_provider_config: {
                provider_name: 'test_provider',
                provider_config: {
                    allow_group_messages: true,
                    process_offline_messages: false
                }
            },
            queue_config: {
                max_messages: 10,
                max_characters: 1000,
                max_days: 1,
                max_characters_single_message: 300
            },
            context_config: {},
            llm_provider_config: {
                provider_name: 'openai',
                provider_config: {
                    api_key: 'sk-test',
                    model: 'gpt-4',
                    temperature: 0.7,
                    record_llm_interactions: true
                }
            }
        },
        features: {
            automatic_bot_reply: {
                enabled: true,
                respond_to_whitelist: ['12345'],
                respond_to_whitelist_group: [],
                chat_system_prompt: 'You are a bot.'
            },
            periodic_group_tracking: {
                enabled: false,
                tracked_groups: []
            },
            kid_phone_safety_tracking: {
                enabled: false
            }
        }
    };

    test('should validate a correct configuration object', () => {
        const result = validateConfiguration(validConfig);
        expect(result.isValid).toBe(true);
        expect(result.errors).toEqual([]);
    });

    test('should validate an array of configuration objects', () => {
        const result = validateConfiguration([validConfig, { ...validConfig, bot_id: 'bot2' }]);
        expect(result.isValid).toBe(true);
    });

    // --- UserConfiguration Level ---

    test('should fail if bot_id is missing', () => {
        const invalid = { ...validConfig, bot_id: undefined };
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('bot_id is required');
    });

    test('should fail if configurations is missing', () => {
        const invalid = { ...validConfig, configurations: undefined };
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('configurations is required');
    });

    // --- ConfigurationsSettings Level ---

    test('should fail if chat_provider_config is missing', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        delete invalid.configurations.chat_provider_config;
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('chat_provider_config is required');
    });

    test('should fail if llm_provider_config is missing', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        delete invalid.configurations.llm_provider_config;
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('llm_provider_config is required');
    });

    // --- ChatProviderSettings Level ---

    test('should fail if allow_group_messages is not a boolean', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.configurations.chat_provider_config.provider_config.allow_group_messages = 'yes';
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('must be a boolean');
    });

    // --- QueueConfig Level ---

    test('should fail if max_messages is not a number', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.configurations.queue_config.max_messages = '10';
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('must be a number');
    });

    // --- LLMProviderSettings Level ---

    test('should fail if api_key is not a string or null', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.configurations.llm_provider_config.provider_config.api_key = 123;
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('must be a string');
    });

    test('should fail if model is missing', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        delete invalid.configurations.llm_provider_config.provider_config.model;
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('model is required');
    });

    test('should fail if temperature is not a number', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.configurations.llm_provider_config.provider_config.temperature = 'hot';
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('temperature must be a number');
    });

    // --- Feature Level ---

    test('should fail if automatic_bot_reply.enabled is not boolean', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.features.automatic_bot_reply.enabled = 1;
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('enabled must be a boolean');
    });

    test('should fail if respond_to_whitelist is not an array', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.features.automatic_bot_reply.respond_to_whitelist = '123';
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('whitelist must be an array');
    });

    test('should fail if tracked_groups is not an array', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.features.periodic_group_tracking.tracked_groups = {};
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('tracked_groups must be an array');
    });

    test('should fail if user_details.first_name is not a string', () => {
        const invalid = JSON.parse(JSON.stringify(validConfig));
        invalid.configurations.user_details.first_name = 123;
        const result = validateConfiguration(invalid);
        expect(result.isValid).toBe(false);
        expect(result.errors[0].message).toContain('first_name must be a string');
    });

});
