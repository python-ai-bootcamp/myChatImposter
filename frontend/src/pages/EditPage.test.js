import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import EditPage from './EditPage';

// Mock the global fetch function
global.fetch = jest.fn();

// Mock useNavigate
const mockedNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockedNavigate,
}));

const mockSchema = {
  title: 'User Configuration',
  type: 'object',
  properties: {
    bot_id: { type: 'string', title: 'Bot ID' },
    configurations: {
      type: 'object',
      title: 'General Configurations',
      properties: {
        queue_config: {
          type: 'object',
          title: 'Queue Config',
          properties: {
            max_messages: { type: 'number', title: 'Max Messages' }
          }
        },
        llm_provider_config: { type: 'object', title: 'LLM Provider Config' },
        chat_provider_config: {
          type: 'object',
          title: 'Chat Provider Config',
          properties: {
            provider_config: {
              type: 'object',
              properties: {
                allow_group_messages: { type: 'boolean', title: 'Allow Group Messages' }
              }
            }
          }
        },
      }
    },
    features: {
      type: 'object',
      title: 'Feature Configurations',
      properties: {
        automatic_bot_reply: {
          type: 'object',
          title: 'Automatic Bot Reply',
          properties: {
            enabled: { type: 'boolean', title: 'Enabled' },
            respond_to_whitelist: { type: 'array', items: { type: 'string' } }
          }
        },
        periodic_group_tracking: {
          type: 'object',
          title: 'Periodic Group Tracking',
          properties: {
            enabled: { type: 'boolean', title: 'Enabled' },
            tracked_groups: { type: 'array', items: { type: 'object' } }
          }
        },
        kid_phone_safety_tracking: {
          type: 'object',
          title: 'Kid Phone Safety Tracking',
          properties: {
            enabled: { type: 'boolean', title: 'Enabled' }
          }
        }
      }
    }
  },
};

let mockInitialData = {
  bot_id: 'test-bot',
  configurations: {
    queue_config: {
      max_messages: 10
    },
    chat_provider_config: {
      provider_name: 'test',
      provider_config: {
        allow_group_messages: false
      }
    }
  },
  features: {
    automatic_bot_reply: {
      enabled: false,
      respond_to_whitelist: ['user1'],
      respond_to_whitelist_group: []
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

beforeEach(() => {
  fetch.mockClear();
  mockedNavigate.mockClear();
});

const renderComponent = () => {
  fetch.mockImplementation((url) => {
    if (url.includes('/api/external/bots/schema')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSchema),
      });
    }
    // New defaults endpoint
    if (url.includes('/api/external/bots/defaults')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockInitialData),
      });
    }
    // GET /api/external/bots/{botId}
    if (url.includes('/api/external/bots/test-bot')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockInitialData), // Return object, not array [mockInitialData] (FastAPI returns Pydantic model)
      });
    }
    // PUT /api/external/bots/{botId}
    if (url.includes('/api/external/bots/')) {
      // Start/Link/Reload actions
      if (url.includes('/actions/')) {
        return Promise.resolve({ ok: true, json: () => ({ status: 'success' }) });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'success' }),
      });
    }
    // Resources
    if (url.includes('/api/external/resources/timezones')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(['UTC', 'Europe/London']) });
    }
    if (url.includes('/api/external/resources/languages')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([{ code: 'en', name: 'English', native_name: 'English' }]) });
    }
    // Chatbot status
    if (url.includes('/chatbot/')) {
      return Promise.resolve({
        ok: false,
        status: 404,
      });
    }
    return Promise.reject(new Error(`Unhandled fetch call: ${url}`));
  });


  render(
    <MemoryRouter initialEntries={['/edit/test-bot']}>
      <Routes>
        <Route path="/edit/:botId" element={<EditPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('renders General Configurations and Feature Configurations sections', async () => {
  renderComponent();

  // The main collapsible sections should be rendered
  const generalConfigHeader = await screen.findByText(/General Configurations/);
  expect(generalConfigHeader).toBeInTheDocument();

  const featureConfigHeader = await screen.findByText(/Feature Configurations/);
  expect(featureConfigHeader).toBeInTheDocument();
});

test('renders the form and saves updated data with new structure', async () => {
  mockInitialData.configurations.llm_provider_config = { provider_name: 'test_provider' };
  renderComponent();

  // Expand General Configurations
  const generalConfigHeader = await screen.findByText(/General Configurations/);
  fireEvent.click(generalConfigHeader);

  // Expand Queue Config
  const queueConfigHeader = await screen.findByText(/Queue Config/);
  fireEvent.click(queueConfigHeader);

  const maxMessagesInput = await screen.findByLabelText(/Max Messages/);
  expect(maxMessagesInput).toBeInTheDocument();
  expect(maxMessagesInput.value).toBe('10');

  fireEvent.change(maxMessagesInput, { target: { value: '50' } });
  expect(maxMessagesInput.value).toBe('50');

  const saveButton = screen.getByRole('button', { name: /^Save$/i });
  fireEvent.click(saveButton);

  await waitFor(() => {
    const putCall = fetch.mock.calls.find(call => call[1] && call[1].method === 'PUT');
    expect(putCall).toBeDefined();
    expect(putCall[0]).toBe('/api/external/bots/test-bot');

    const savedData = JSON.parse(putCall[1].body);
    expect(savedData.configurations.queue_config.max_messages).toBe(50);
  });

  expect(mockedNavigate).toHaveBeenCalledWith('/');
});

test('renders Feature Configurations with all three features', async () => {
  renderComponent();

  // Expand Feature Configurations
  const featureConfigHeader = await screen.findByText(/Feature Configurations/);
  fireEvent.click(featureConfigHeader);

  // All three features should be visible as sub-sections
  const automaticBotReply = await screen.findByText(/Automatic Bot Reply/);
  expect(automaticBotReply).toBeInTheDocument();

  const periodicGroupTracking = await screen.findByText(/Periodic Group Tracking/);
  expect(periodicGroupTracking).toBeInTheDocument();

  const kidPhoneSafety = await screen.findByText(/Kid Phone Safety Tracking/);
  expect(kidPhoneSafety).toBeInTheDocument();
});

test('renders complex nested data correctly with new structure', async () => {
  // Set up mock data that includes multiple fields
  mockInitialData = {
    bot_id: 'test-bot',
    configurations: {
      queue_config: {
        max_messages: 25,
      },
      chat_provider_config: {
        provider_name: 'test',
        provider_config: {
          allow_group_messages: true,
        }
      },
      llm_provider_config: {
        provider_name: 'test_provider'
      },
    },
    features: {
      automatic_bot_reply: {
        enabled: true,
        respond_to_whitelist: ['user1'],
        respond_to_whitelist_group: []
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
  renderComponent();

  // --- Check Live JSON Editor for all data ---
  const jsonEditor = await screen.findByRole('textbox', { name: /Live JSON Editor/i });
  const editorData = JSON.parse(jsonEditor.value);

  // Check that the new structure is present
  expect(editorData.configurations).toBeDefined();
  expect(editorData.configurations.queue_config.max_messages).toBe(25);
  expect(editorData.configurations.chat_provider_config.provider_config.allow_group_messages).toBe(true);
  expect(editorData.configurations.llm_provider_config.provider_name).toBe('test_provider');

  expect(editorData.features).toBeDefined();
  expect(editorData.features.automatic_bot_reply.enabled).toBe(true);
  expect(editorData.features.automatic_bot_reply.respond_to_whitelist).toEqual(['user1']);
});
