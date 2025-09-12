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
    user_id: { type: 'string', title: 'User ID' },
    respond_to_whitelist: { type: 'array', items: { type: 'string', default: '' }, title: 'Whitelist' },
    queue_config: { '$ref': '#/$defs/QueueConfig' },
    llm_provider_config: {
      title: 'LLM Provider Config',
      anyOf: [
        { '$ref': '#/$defs/LlmProviderConfig' },
        { type: 'null', title: 'None' }
      ]
    },
    chat_provider_config: { '$ref': '#/$defs/ChatProviderConfig' }
  },
  required: ['user_id', 'queue_config'],
  '$defs': {
    QueueConfig: {
      type: 'object',
      title: 'Queue Config',
      properties: { max_messages: { type: 'number', title: 'Max Messages' } },
      required: ['max_messages']
    },
    LlmProviderConfig: {
      title: 'LLM Provider',
      oneOf: [
        {
          title: 'OpenAI',
          type: 'object',
          properties: {
            provider_name: { const: 'openAi', title: 'Provider Name' },
            provider_config: {
                type: 'object',
                title: 'OpenAI Config',
                properties: {
                    model: { type: 'string', title: 'Model' },
                    api_key_source: { type: 'string', title: 'API Key Source', enum: ['environment', 'explicit'], default: 'environment' },
                    api_key: { type: 'string', title: 'API Key' }
                }
            }
          }
        }
      ]
    },
    ChatProviderConfig: {
        type: 'object',
        title: 'Chat Provider',
        properties: { some_prop: { type: 'string', title: 'Some Chat Prop' } }
    }
  }
};

const mockInitialData = {
    user_id: 'test-user',
    respond_to_whitelist: ['user1'],
    queue_config: { max_messages: 10 },
    llm_provider_config: {
      provider_name: 'openAi',
      provider_config: {
          model: 'gpt-4',
          api_key_source: 'environment',
          api_key: null // Initially null because source is environment
      }
    },
    chat_provider_config: { some_prop: 'hello' }
};

beforeEach(() => {
  fetch.mockClear();
  mockedNavigate.mockClear();
});

const renderComponent = (userId = 'test-user') => {
    fetch.mockImplementation((url, options) => {
        if (url.includes('/api/configurations/schema')) {
            return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSchema) });
        }
        if (options?.method === 'PUT') {
            return Promise.resolve({ ok: true, json: () => Promise.resolve({ status: 'success' }) });
        }
        if (url.includes(`/api/configurations/${userId}`)) {
            return Promise.resolve({ ok: true, json: () => Promise.resolve(mockInitialData) });
        }
        return Promise.reject(new Error(`Unhandled fetch call: ${url}`));
    });

  render(
    <MemoryRouter initialEntries={[`/edit/${userId}`]}>
      <Routes>
        <Route path="/edit/:userId" element={<EditPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('conditionally renders api_key field based on api_key_source', async () => {
    renderComponent();

    // The API Key Source dropdown should be visible
    const apiKeySourceSelect = await screen.findByLabelText('API Key Source');
    expect(apiKeySourceSelect).toBeInTheDocument();
    expect(apiKeySourceSelect.value).toBe('environment');

    // The API Key input should NOT be visible initially
    expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument();

    // Change the source to 'explicit'
    fireEvent.change(apiKeySourceSelect, { target: { value: 'explicit' } });

    // The API Key input should now appear
    const apiKeyInput = await screen.findByLabelText('API Key');
    expect(apiKeyInput).toBeInTheDocument();

    // Change it back to 'environment'
    fireEvent.change(apiKeySourceSelect, { target: { value: 'environment' } });

    // The API Key input should disappear again
    await waitFor(() => {
        expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument();
    });
});
