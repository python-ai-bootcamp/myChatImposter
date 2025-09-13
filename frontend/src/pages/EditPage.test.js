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
    respond_to_whitelist: { type: 'array', items: { type: 'string' } },
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
        allow_group_messages: { type: 'boolean', title: 'Allow Group Messages' }
      }
    },
  },
};

let mockInitialData = {
    user_id: 'test-user',
    respond_to_whitelist: ['user1'],
    queue_config: {
        max_messages: 10
    },
    // llm_provider_config is intentionally missing to test the fix
};

beforeEach(() => {
  fetch.mockClear();
  mockedNavigate.mockClear();
});

const renderComponent = () => {
    fetch.mockImplementation((url) => {
        if (url.includes('/api/configurations/schema')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve(mockSchema),
            });
        }
        if (url.includes('/api/configurations/test-user')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([mockInitialData]),
            });
        }
        if (url.includes('/api/configurations/')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ status: 'success' }),
            });
        }
        return Promise.reject(new Error(`Unhandled fetch call: ${url}`));
    });


  render(
    <MemoryRouter initialEntries={['/edit/test-user']}>
      <Routes>
        <Route path="/edit/:userId" element={<EditPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('renders all sections even when data is missing for a group', async () => {
  renderComponent();

  // The LlmBotConfig section should be rendered, even though llm_provider_config is missing from the initial data
  const llmBotConfigHeader = await screen.findByText(/LlmBotConfig/);
  expect(llmBotConfigHeader).toBeInTheDocument();

  // Expand the section
  fireEvent.click(llmBotConfigHeader);

  // The inner field should be rendered (rjsf will handle rendering the field for a null value)
  // We can check for the title of the field inside the group.
  const llmProviderField = await screen.findByText(/LLM Provider Config/);
  expect(llmProviderField).toBeInTheDocument();
});

test('renders the form and saves updated data', async () => {
  // Restore the full data for this test
  mockInitialData.llm_provider_config = { some: 'data' };
  renderComponent();

  const queueConfigHeader = await screen.findByText(/Queue Config/);
  fireEvent.click(queueConfigHeader);

  const maxMessagesInput = await screen.findByLabelText(/Max Messages/);
  expect(maxMessagesInput).toBeInTheDocument();
  expect(maxMessagesInput.value).toBe('10');

  fireEvent.change(maxMessagesInput, { target: { value: '50' } });
  expect(maxMessagesInput.value).toBe('50');

  const saveButton = screen.getByRole('button', { name: /Save/i });
  fireEvent.click(saveButton);

  await waitFor(() => {
    const expectedBody = [{
        ...mockInitialData,
        queue_config: {
            ...mockInitialData.queue_config,
            max_messages: 50,
        }
    }];

    const putCall = fetch.mock.calls.find(call => call[1] && call[1].method === 'PUT');
    expect(putCall).toBeDefined();
    expect(putCall[0]).toBe('/api/configurations/test-user');
    expect(JSON.parse(putCall[1].body)).toEqual(expectedBody);
  });

  expect(mockedNavigate).toHaveBeenCalledWith('/');
});

test('renders complex nested data correctly', async () => {
  // Set up mock data that includes multiple fields that were failing
  mockInitialData = {
    user_id: 'test-user',
    respond_to_whitelist: ['user1'],
    queue_config: {
      max_messages: 25,
    },
    chat_provider_config: {
      allow_group_messages: true,
    },
    llm_provider_config: {
      provider_name: 'test_provider'
    },
  };
  renderComponent();

  // --- Check Chat Provider Config ---
  const chatConfigHeader = await screen.findByText(/Chat Provider Config/);
  fireEvent.click(chatConfigHeader);
  const allowGroupMessagesCheckbox = await screen.findByLabelText('Allow Group Messages');
  expect(allowGroupMessagesCheckbox).toBeChecked();

  // --- Check Queue Config ---
  const queueConfigHeader = await screen.findByText(/Queue Config/);
  fireEvent.click(queueConfigHeader);
  const maxMessagesInput = await screen.findByLabelText('Max Messages');
  expect(maxMessagesInput.value).toBe('25');

  // --- Check Live JSON Editor for all data ---
  const jsonEditor = await screen.findByRole('textbox', { name: /Live JSON Editor/i });
  const editorData = JSON.parse(jsonEditor.value);

  // Check that all original top-level keys are present
  expect(editorData.chat_provider_config).toBeDefined();
  expect(editorData.chat_provider_config.allow_group_messages).toBe(true);

  expect(editorData.queue_config).toBeDefined();
  expect(editorData.queue_config.max_messages).toBe(25);

  expect(editorData.llm_provider_config).toBeDefined();
  expect(editorData.llm_provider_config.provider_name).toBe('test_provider');

  expect(editorData.respond_to_whitelist).toEqual(['user1']);
});
