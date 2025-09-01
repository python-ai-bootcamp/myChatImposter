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
    }
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
    // Setup mock fetches for both schema and data
    fetch.mockImplementation((url) => {
        if (url.includes('/api/configurations/schema')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve(mockSchema),
            });
        }
        if (url.includes('/api/configurations/test.json')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve(mockInitialData),
            });
        }
        // Mock the save PUT request
        if (url.includes('/api/configurations/')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ status: 'success' }),
            });
        }
        return Promise.reject(new Error(`Unhandled fetch call: ${url}`));
    });


  render(
    <MemoryRouter initialEntries={['/edit/test.json']}>
      <Routes>
        <Route path="/edit/:filename" element={<EditPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('renders the form and saves updated data', async () => {
  renderComponent();

  // Wait for the form to render by finding a field from the schema
  const maxMessagesInput = await screen.findByLabelText('Max Messages');
  expect(maxMessagesInput).toBeInTheDocument();
  expect(maxMessagesinput.value).toBe('10');

  // Change a value
  fireEvent.change(maxMessagesInput, { target: { value: '50' } });
  expect(maxMessagesinput.value).toBe('50');

  // Submit the form
  const saveButton = screen.getByRole('button', { name: /Save/i });
  fireEvent.click(saveButton);

  // Wait for the save operation to complete and check the fetch call
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      '/api/configurations/test.json',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify([{ // The component now wraps the data in an array
            ...mockInitialData,
            queue_config: {
                ...mockInitialData.queue_config,
                max_messages: 50, // The updated value
            }
        }]),
      })
    );
  });

  // Check for navigation
  expect(mockedNavigate).toHaveBeenCalledWith('/');
});
