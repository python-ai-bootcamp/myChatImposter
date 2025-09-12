import { render, screen, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LinkPage from './LinkPage';

// Mock the global fetch function
global.fetch = jest.fn();
// Use fake timers to control setInterval
jest.useFakeTimers();

beforeEach(() => {
  fetch.mockClear();
  jest.clearAllTimers();
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

test('polls for status and stops when connected', async () => {
  // Mock a sequence of status updates
  fetch
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'connecting' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'got qr code', qr: 'data:image/png;base64,full-data-url' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'connected' }) });

  renderComponent('test-user');

  // Initial render -> first poll
  await screen.findByText(/Status: connecting/i);
  expect(fetch).toHaveBeenCalledTimes(1);

  // Advance time -> second poll
  await act(async () => { jest.advanceTimersByTime(2000); });
  const qrImage = await screen.findByAltText('QR Code');
  expect(qrImage).toBeInTheDocument();
  expect(qrImage.src).toBe('data:image/png;base64,full-data-url');
  expect(fetch).toHaveBeenCalledTimes(2);

  // Advance time -> third poll (final status)
  await act(async () => { jest.advanceTimersByTime(2000); });
  await screen.findByText(/Status: connected/i);
  expect(fetch).toHaveBeenCalledTimes(3);

  // Advance time again -> polling should have stopped
  await act(async () => { jest.advanceTimersByTime(2000); });
  // The fetch count should NOT have increased
  expect(fetch).toHaveBeenCalledTimes(3);
});
