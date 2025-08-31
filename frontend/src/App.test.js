import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';

// Mock the global fetch function
global.fetch = jest.fn();

beforeEach(() => {
  fetch.mockClear();
});

test('renders home page, allows file selection, and enables buttons', async () => {
  // Mock the API response for the configuration files
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ files: ['test1.json', 'test2.json'] }),
  });

  render(<App />);

  // Check for the main panel heading
  expect(screen.getByRole('heading', { name: /WhatsApp Imposter Control Panel/i })).toBeInTheDocument();

  // Check that the buttons are initially disabled
  expect(screen.getByRole('button', { name: /Link/i })).toBeDisabled();
  expect(screen.getByRole('button', { name: /Edit/i })).toBeDisabled();

  // Wait for the files to be loaded and displayed
  const file1 = await screen.findByText('test1.json');
  expect(file1).toBeInTheDocument();
  expect(screen.getByText('test2.json')).toBeInTheDocument();

  // Simulate clicking on a file
  fireEvent.click(file1);

  // Check that the file is selected (optional, but good practice)
  expect(file1).toHaveClass('selected');

  // Check that the buttons are now enabled
  expect(screen.getByRole('button', { name: /Link/i })).toBeEnabled();
  expect(screen.getByRole('button', { name: /Edit/i })).toBeEnabled();
});

test('handles API error when fetching files', async () => {
  // Mock a failed API response
  fetch.mockResolvedValueOnce({
    ok: false,
    status: 500,
  });

  render(<App />);

  // Wait for the error message to be displayed
  const errorMessage = await screen.findByText(/Error: Failed to fetch configuration files/i);
  expect(errorMessage).toBeInTheDocument();
});
