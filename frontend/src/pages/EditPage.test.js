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
    chat_provider_config: { type: 'object', title: 'Chat Provider Config' },
  },
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
                json: () => Promise.resolve([mockInitialData]), // The API returns an array
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

test('renders the form and saves updated data', async () => {
  renderComponent();

  // Find and click the header for the "Queue Config" section to expand it
  const queueConfigHeader = await screen.findByText('Queue Config');
  fireEvent.click(queueConfigHeader);

  // Now find the field inside the expanded section
  const maxMessagesInput = await screen.findByLabelText('Max Messages');
  expect(maxMessagesInput).toBeInTheDocument();
  expect(maxMessagesInput.value).toBe('10');

  // Change a value
  fireEvent.change(maxMessagesInput, { target: { value: '50' } });
  expect(maxMessagesInput.value).toBe('50');

  // Submit the form
  const saveButton = screen.getByRole('button', { name: /Save/i });
  fireEvent.click(saveButton);

  // Wait for the save operation to complete and check the fetch call
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

  // Check for navigation
  expect(mockedNavigate).toHaveBeenCalledWith('/');
});
