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
  { user_id: 'user1', status: 'disconnected' },
  { user_id: 'user2', status: 'linking' },
  { user_id: 'user3', status: 'connected' },
];

test('renders files with correct status dots and handles button states', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({ configurations: mockStatuses }),
  });

  render(<App />);

  // Wait for files to be rendered
  const user1 = await screen.findByText('user1');
  const user2 = await screen.findByText('user2');
  const user3 = await screen.findByText('user3');

  // Check for status dots
  expect(user1.closest('tr').querySelector('.status-dot')).toHaveClass('gray');
  expect(user2.closest('tr').querySelector('.status-dot')).toHaveClass('orange');
  expect(user3.closest('tr').querySelector('.status-dot')).toHaveClass('green');

  // --- Test button state for DISCONNECTED ---
  fireEvent.click(user1);
  expect(screen.getByRole('button', { name: /Link/i })).toBeEnabled();
  expect(screen.queryByRole('button', { name: /Unlink/i })).not.toBeInTheDocument();

  // --- Test button state for LINKING ---
  fireEvent.click(user2);
  expect(screen.getByRole('button', { name: /Link/i })).toBeDisabled();
  expect(screen.queryByRole('button', { name: /Unlink/i })).not.toBeInTheDocument();

  // --- Test button state for CONNECTED ---
  fireEvent.click(user3);
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
    json: async () => ({
      configurations: [
        { user_id: 'user1', status: 'disconnected' },
        { user_id: 'user2', status: 'linking' },
        { user_id: 'user3', status: 'disconnected' }, // Status changed
      ]
    }),
  });

  jest.spyOn(window, 'confirm').mockImplementation(() => true);

  render(<App />);

  const connectedUser = await screen.findByText('user3');
  fireEvent.click(connectedUser);

  // Unlink button should now be visible and enabled
  const unlinkButton = screen.getByRole('button', { name: /Unlink/i });
  fireEvent.click(unlinkButton);

  // Check that the DELETE API was called
  await waitFor(() => {
    expect(fetch).toHaveBeenCalledWith('/api/users/user3/actions/unlink', { method: 'POST' });
  });

  // Check that the status dot has changed to gray after the refresh
  await waitFor(() => {
    expect(connectedUser.closest('tr').querySelector('.status-dot')).toHaveClass('gray');
  });

  window.confirm.mockRestore();
});
