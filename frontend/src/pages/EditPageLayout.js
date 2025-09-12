export const editPageLayout = {
  sections: [
    {
      id: 'general',
      title: 'General Configuration',
      fields: [
        { name: 'user_id', hidden: true },
        { name: 'respond_to_whitelist' },
      ],
    },
    {
      id: 'llm',
      title: 'LLM Provider',
      fields: [{ name: 'llm_provider_config' }],
    },
    {
      id: 'chat',
      title: 'Chat Provider',
      fields: [{ name: 'chat_provider_config' }],
    },
    {
      id: 'queue',
      title: 'Queue',
      fields: [{ name: 'queue_config' }],
    },
  ],
};
