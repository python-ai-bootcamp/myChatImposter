// This file defines the layout of the Edit Page.
// The structure has two main collapsible sections: General Configurations and Feature Configurations.
// Each main section contains sub-sections that are also collapsible.

export const editPageLayout = {
  // Main groups at the top level
  groups: {
    // General Configurations - contains system settings
    configurations: {
      title: 'General Configurations',
      fields: ['configurations'],
      // Sub-groups define the collapsible sub-sections within configurations
      subGroups: {
        chat_provider_config: {
          title: 'Chat Provider Config',
          description: 'Settings for the chat provider connection'
        },
        queue_config: {
          title: 'Queue Config',
          description: 'Message queue settings'
        },
        context_config: {
          title: 'Context Config',
          description: 'LLM context window settings'
        },
        llm_provider_config: {
          title: 'LLM Provider Config',
          description: 'Language model provider settings'
        }
      }
    },
    // Feature Configurations - contains toggleable feature modules
    features: {
      title: 'Feature Configurations',
      fields: ['features'],
      // Sub-groups define the collapsible sub-sections for each feature
      subGroups: {
        automatic_bot_reply: {
          title: 'Automatic Bot Reply',
          description: 'Automatically reply to whitelisted contacts and groups'
        },
        periodic_group_tracking: {
          title: 'Periodic Group Tracking',
          description: 'Track group activities on a schedule'
        },
        kid_phone_safety_tracking: {
          title: 'Kid Phone Safety Tracking',
          description: 'Monitor messages for child safety'
        }
      }
    }
  }
};
