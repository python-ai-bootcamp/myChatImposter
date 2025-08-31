import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LinkPage from './LinkPage';

// Mock the global fetch function
global.fetch = jest.fn();
// Use fake timers to control setInterval
jest.useFakeTimers();

beforeEach(() => {
  fetch.mockClear();
});

afterEach(() => {
    // Restore real timers
    jest.useRealTimers();
});

const renderComponent = () => {
  render(
    <MemoryRouter initialEntries={['/link/test.json']}>
      <Routes>
        <Route path="/link/:filename" element={<LinkPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('renders, creates instance, and polls for status', async () => {
  // 1. Mock config fetch
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ([{ user_id: 'test-user' }]),
  });

  // 2. Mock instance creation
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      successful: [{ user_id: 'test-user', instance_id: 'abc-123' }],
      failed: [],
    }),
  });

  // 3. Mock status poll (first time)
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'connecting' }),
  });

  // 4. Mock status poll (second time, with QR code)
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'got qr code', qr: 'data:image/png;base64,qr-code-string' }),
  });

  renderComponent();

  // Wait for user_id to be displayed after creation
  await screen.findByText('User ID: test-user');
  expect(screen.getByText('Status: Instance created. Waiting for status...')).toBeInTheDocument();

  // Advance timers to trigger the first poll
  await act(async () => {
    jest.advanceTimersByTime(2000);
  });

  // Wait for status to update from the first poll
  await screen.findByText('Status: connecting');

  // Advance timers to trigger the second poll
  await act(async () => {
    jest.advanceTimersByTime(2000);
  });

  // Wait for QR code to be displayed from the second poll
  const qrCodeImage = await screen.findByAltText('QR Code');
  expect(qrCodeImage).toBeInTheDocument();
  expect(qrCodeImage.src).toBe('data:image/png;base64,qr-code-string');

  // Check that fetch was called for the status poll with the user_id
  expect(fetch).toHaveBeenCalledWith('/chatbot/test-user/status');
});
