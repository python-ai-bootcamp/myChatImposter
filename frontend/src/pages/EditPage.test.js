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
                properties: { model: { type: 'string', title: 'Model' } }
            }
          }
        },
        {
          title: 'FakeLLM',
          type: 'object',
          properties: {
            provider_name: { const: 'fakeLlm', title: 'Provider Name' },
            provider_config: {
                type: 'object',
                title: 'FakeLLM Config',
                properties: { dummy_value: { type: 'string', title: 'Dummy Value' } }
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
      provider_config: { model: 'gpt-4' }
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

test('handles anyOf fields with null option', async () => {
    renderComponent();

    // The dropdown for the provider should be visible, with "LLM Provider" selected.
    // Note: The title for the selected oneOf/anyOf sub-schema is used.
    const providerSelect = await screen.findByDisplayValue('LLM Provider');
    expect(providerSelect).toBeInTheDocument();

    // The field for the initially selected provider should be visible
    let modelInput = await screen.findByLabelText('Model');
    expect(modelInput).toBeInTheDocument();

    // Change the provider to "None"
    fireEvent.change(providerSelect, { target: { value: 'None' } });

    // The sub-form should disappear
    await waitFor(() => {
        expect(screen.queryByLabelText('Model')).not.toBeInTheDocument();
    });

    // Save the form
    const saveButton = screen.getByRole('button', { name: /Save/i });
    fireEvent.click(saveButton);

    // Check that the saved data has a null value for the provider
    await waitFor(() => {
        const putCall = fetch.mock.calls.find(call => call[1] && call[1].method === 'PUT');
        expect(putCall).toBeDefined();
        const savedData = JSON.parse(putCall[1].body)[0];
        expect(savedData.llm_provider_config).toBeNull();
    });
});
