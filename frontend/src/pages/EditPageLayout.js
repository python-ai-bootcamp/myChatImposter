// This file defines the layout of the Edit Page.
// By editing this file, you can change which fields appear in which collapsible section.

export const editPageLayout = {
  // Each key represents a new group that will be created in the form.
  // The 'title' will be the display name of the collapsible section.
  // The 'fields' array lists the top-level properties from the schema that should be moved into this group.
  groups: {
    general_config: {
      title: 'General Config',
      fields: ['user_id', 'respond_to_whitelist'],
    },
    llm_bot_config: {
      title: 'LlmBotConfig',
      fields: ['llm_provider_config'],
    },
    chat_provider_config: {
      title: 'Chat Provider Config',
      fields: ['chat_provider_config'],
    },
    queue_config: {
      title: 'Queue Config',
      fields: ['queue_config'],
    },
  },
};
