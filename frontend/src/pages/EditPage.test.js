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

beforeEach(() => {
  fetch.mockClear();
  mockedNavigate.mockClear();
});

const renderComponent = () => {
  render(
    <MemoryRouter initialEntries={['/edit/test.json']}>
      <Routes>
        <Route path="/edit/:filename" element={<EditPage />} />
      </Routes>
    </MemoryRouter>
  );
};

test('fetches and displays file content', async () => {
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ key: 'value' }),
  });

  renderComponent();

  const textArea = await screen.findByRole('textbox');
  await waitFor(() => {
    expect(JSON.parse(textArea.value)).toEqual({ key: 'value' });
  });
});

test('shows an error for invalid JSON on save', async () => {
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({}),
  });
  renderComponent();

  const textArea = await screen.findByRole('textbox');
  fireEvent.change(textArea, { target: { value: '{"key": "value"' } }); // Invalid JSON

  fireEvent.click(screen.getByRole('button', { name: /Save/i }));

  const errorMessage = await screen.findByText(/Invalid JSON/i);
  expect(errorMessage).toBeInTheDocument();
});

test('successfully saves a JSON array', async () => {
  // Mock initial fetch
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({}),
  });

  // Mock save fetch
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'success' }),
  });

  renderComponent();

  const textArea = await screen.findByRole('textbox');
  const arrayContent = JSON.stringify([{ id: 1 }, { id: 2 }], null, 2);
  fireEvent.change(textArea, { target: { value: arrayContent } });

  fireEvent.click(screen.getByRole('button', { name: /Save/i }));

  await waitFor(() => {
    expect(mockedNavigate).toHaveBeenCalledWith('/');
  });
});

test('successfully saves valid JSON object', async () => {
  // Mock initial fetch
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ key: 'old value' }),
  });

  // Mock save fetch
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ status: 'success' }),
  });

  renderComponent();

  const textArea = await screen.findByRole('textbox');
  await waitFor(() => {
      // Wait for the initial content to be loaded
      expect(JSON.parse(textArea.value)).toEqual({ key: 'old value' });
  });

  fireEvent.change(textArea, { target: { value: '{"key": "new value"}' } });

  fireEvent.click(screen.getByRole('button', { name: /Save/i }));

  await waitFor(() => {
    expect(mockedNavigate).toHaveBeenCalledWith('/');
  });
});
