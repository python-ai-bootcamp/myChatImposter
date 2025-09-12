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
        type: 'object',
        title: 'LLM Provider',
        properties: {}
    },
    chat_provider_config: {
        type: 'object',
        title: 'Chat Provider',
        properties: {}
    }
  },
  required: ['user_id', 'queue_config']
};

const mockInitialData = {
    user_id: 'test-user',
    respond_to_whitelist: ['user1'],
    queue_config: {
        max_messages: 10
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

test('renders the form with nested fields and saves updated data', async () => {
  renderComponent();

  const maxMessagesInput = await screen.findByLabelText('Max Messages');
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

test('displays a validation error for invalid data', async () => {
    renderComponent();

    const maxMessagesInput = await screen.findByLabelText('Max Messages');
    expect(maxMessagesInput).toBeInTheDocument();

    fireEvent.change(maxMessagesInput, { target: { value: '' } });

    // The error from AJV for a type mismatch is "must be number"
    const errorMessage = await screen.findByText('must be number');
    expect(errorMessage).toBeInTheDocument();

    const saveButton = screen.getByRole('button', { name: /Save/i });
    expect(saveButton).toBeDisabled();
});
