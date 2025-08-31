import { render, screen, act } from '@testing-library/react';
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

const renderComponent = (userId) => {
  render(
    <MemoryRouter initialEntries={[`/link/${userId}`]}>
      <Routes>
        <Route path="/link/:userId" element={<LinkPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('polls for status and displays qr code', async () => {
  // 1. Mock status poll (first time)
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'connecting' }),
  });

  // 2. Mock status poll (second time, with QR code)
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'got qr code', qr: 'data:image/png;base64,qr-code-string' }),
  });

  renderComponent('test-user');

  // Initial render shows the user id and initial status
  expect(screen.getByText('Link Status for User: test-user')).toBeInTheDocument();
  // The first poll is called immediately
  await screen.findByText('Status: connecting');

  // Advance timers to trigger the second poll
  await act(async () => {
    jest.advanceTimersByTime(2000);
  });

  // Wait for QR code to be displayed from the second poll
  const qrCodeImage = await screen.findByAltText('QR Code');
  expect(qrCodeImage).toBeInTheDocument();
  expect(qrCodeImage.src).toBe('data:image/png;base64,qr-code-string');
  expect(screen.getByText('Status: got qr code')).toBeInTheDocument();

  // Check that fetch was called for the status poll with the user_id
  expect(fetch).toHaveBeenCalledWith('/chatbot/test-user/status');
});
