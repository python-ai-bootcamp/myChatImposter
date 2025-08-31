import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import App from './App';

// Mock the global fetch function
global.fetch = jest.fn();

// Mock useNavigate
const mockedNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockedNavigate,
}));

// Use fake timers to control setInterval
jest.useFakeTimers();

beforeEach(() => {
  fetch.mockClear();
  mockedNavigate.mockClear();
  jest.clearAllTimers();
});

afterEach(() => {
    jest.useRealTimers();
});

const mockStatuses = [
  { filename: 'disconnected.json', user_id: 'user1', status: 'disconnected' },
  { filename: 'linking.json', user_id: 'user2', status: 'linking' },
  { filename: 'connected.json', user_id: 'user3', status: 'connected' },
];

test('renders files with correct status dots and handles button states', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({ configurations: mockStatuses }),
  });

  render(<App />);

  // Wait for files to be rendered
  const file1 = await screen.findByText('disconnected.json');
  const file2 = await screen.findByText('linking.json');
  const file3 = await screen.findByText('connected.json');

  // Check for status dots
  expect(file1.querySelector('.status-dot')).toHaveClass('gray');
  expect(file2.querySelector('.status-dot')).toHaveClass('orange');
  expect(file3.querySelector('.status-dot')).toHaveClass('green');

  // --- Test button state for DISCONNECTED ---
  fireEvent.click(file1);
  expect(screen.getByRole('button', { name: /Link/i })).toBeEnabled();
  expect(screen.queryByRole('button', { name: /Unlink/i })).not.toBeInTheDocument();

  // --- Test button state for LINKING ---
  fireEvent.click(file2);
  expect(screen.getByRole('button', { name: /Link/i })).toBeDisabled();
  expect(screen.queryByRole('button', { name: /Unlink/i })).not.toBeInTheDocument();

  // --- Test button state for CONNECTED ---
  fireEvent.click(file3);
  expect(screen.getByRole('button', { name: 'Unlink' })).toBeEnabled();
  expect(screen.queryByRole('button', { name: 'Link' })).not.toBeInTheDocument();
});

test('Unlink button successfully unlinks a user', async () => {
  // Initial status
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ configurations: mockStatuses }),
  });
  // Mock the DELETE request
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'success' }),
  });
  // Mock the refresh call after delete
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ configurations: [
        { filename: 'disconnected.json', user_id: 'user1', status: 'disconnected' },
        { filename: 'linking.json', user_id: 'user2', status: 'linking' },
        { filename: 'connected.json', user_id: 'user3', status: 'disconnected' }, // Status changed
    ]}),
  });

  jest.spyOn(window, 'confirm').mockImplementation(() => true);

  render(<App />);

  const connectedFile = await screen.findByText('connected.json');
  fireEvent.click(connectedFile);

  // Unlink button should now be visible and enabled
  const unlinkButton = screen.getByRole('button', { name: /Unlink/i });
  fireEvent.click(unlinkButton);

  // Check that the DELETE API was called
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith('/chatbot/user3', { method: 'DELETE' });
  });

  // Check that the status dot has changed to gray after the refresh
  await waitFor(() => {
    expect(connectedFile.querySelector('.status-dot')).toHaveClass('gray');
  });

  window.confirm.mockRestore();
});
