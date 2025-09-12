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
    queue_config: {
        type: 'object',
        title: 'Queue Config',
        properties: {
            max_messages: { type: 'number', title: 'Max Messages' }
        },
        required: ['max_messages']
    },
    llm_provider_config: {
      title: 'LLM Provider Config',
      oneOf: [
        {
          title: 'OpenAI',
          type: 'object', // Added this
          properties: {
            provider_name: { const: 'openAi', title: 'Provider Name' },
            provider_config: {
                type: 'object',
                title: 'OpenAI Config',
                properties: {
                    model: { type: 'string', title: 'Model' }
                }
            }
          }
        },
        {
          title: 'FakeLLM',
          type: 'object', // Added this
          properties: {
            provider_name: { const: 'fakeLlm', title: 'Provider Name' },
            provider_config: {
                type: 'object',
                title: 'FakeLLM Config',
                properties: {
                    dummy_value: { type: 'string', title: 'Dummy Value' }
                }
            }
          }
        }
      ]
    },
    chat_provider_config: {
        type: 'object',
        title: 'Chat Provider',
        properties: {}
    }
  },
  required: ['user_id', 'queue_config', 'llm_provider_config']
};

const mockInitialData = {
    user_id: 'test-user',
    respond_to_whitelist: ['user1'],
    queue_config: {
        max_messages: 10
    },
    llm_provider_config: {
      provider_name: 'openAi',
      provider_config: {
        model: 'gpt-4'
      }
    }
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
        if (options && options.method === 'PUT' && url.includes(`/api/configurations/${userId}`)) {
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

test('handles oneOf fields by rendering a dropdown and switching sub-forms', async () => {
    renderComponent();

    const providerSelect = await screen.findByDisplayValue('OpenAI');
    expect(providerSelect).toBeInTheDocument();

    let modelInput = await screen.findByLabelText('Model');
    expect(modelInput).toBeInTheDocument();
    expect(modelInput.value).toBe('gpt-4');

    expect(screen.queryByLabelText('Dummy Value')).not.toBeInTheDocument();

    fireEvent.change(providerSelect, { target: { value: 'FakeLLM' } });

    await waitFor(() => {
        expect(screen.queryByLabelText('Model')).not.toBeInTheDocument();
    });

    const dummyInput = await screen.findByLabelText('Dummy Value');
    expect(dummyInput).toBeInTheDocument();

    fireEvent.change(dummyInput, { target: { value: 'test-dummy' } });
    expect(dummyInput.value).toBe('test-dummy');

    const saveButton = screen.getByRole('button', { name: /Save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
        const putCall = fetch.mock.calls.find(call => call[1] && call[1].method === 'PUT');
        expect(putCall).toBeDefined();
        const savedData = JSON.parse(putCall[1].body)[0];
        expect(savedData.llm_provider_config.provider_name).toBe('fakeLlm');
        expect(savedData.llm_provider_config.provider_config.dummy_value).toBe('test-dummy');
    });
});
