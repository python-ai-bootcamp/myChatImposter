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

test('successfully adds a new file', async () => {
  // Initial file list
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ files: ['existing.json'] }),
  });
  // Mock the PUT request for the new file
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'success' }),
  });
  // Mock the refresh call
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ files: ['existing.json', 'new-file.json'] }),
  });

  // Mock the prompt
  jest.spyOn(window, 'prompt').mockImplementation(() => 'new-file.json');

  render(<App />);

  // Wait for initial files to load
  await screen.findByText('existing.json');

  // Click the add button
  fireEvent.click(screen.getByRole('button', { name: /Add/i }));

  // Wait for the new file to appear in the list
  const newFile = await screen.findByText('new-file.json');
  expect(newFile).toBeInTheDocument();

  // Clean up the mock
  window.prompt.mockRestore();
});

test('successfully deletes a file', async () => {
  // Initial file list
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ files: ['file-to-delete.json', 'other-file.json'] }),
  });
  // Mock the DELETE request
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'success' }),
  });
  // Mock the refresh call
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ files: ['other-file.json'] }),
  });

  // Mock the confirm
  jest.spyOn(window, 'confirm').mockImplementation(() => true);

  render(<App />);

  // Find and select the file to delete
  const fileToDelete = await screen.findByText('file-to-delete.json');
  fireEvent.click(fileToDelete);

  // Click the delete button
  fireEvent.click(screen.getByRole('button', { name: /Delete/i }));

  // Wait for the file to be removed from the DOM
  await waitFor(() => {
    expect(screen.queryByText('file-to-delete.json')).not.toBeInTheDocument();
  });

  // Check that the other file is still there
  expect(screen.getByText('other-file.json')).toBeInTheDocument();

  // Clean up the mock
  window.confirm.mockRestore();
});
