import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the main page', () => {
  render(<App />);
  const headingElement = screen.getByText(/WhatsApp Imposter Control Panel/i);
  expect(headingElement).toBeInTheDocument();

  const buttonElement = screen.getByText(/Create User/i);
  expect(buttonElement).toBeInTheDocument();
});
