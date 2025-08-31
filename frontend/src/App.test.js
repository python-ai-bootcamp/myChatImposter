import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the main application page with routing', () => {
  render(<App />);

  // Check for the main panel heading
  const mainHeadingElement = screen.getByRole('heading', { name: /WhatsApp Imposter Control Panel/i });
  expect(mainHeadingElement).toBeInTheDocument();

  // Since the default route is HomePage, check for its heading
  const homePageHeading = screen.getByRole('heading', { name: /Configuration Files/i });
  expect(homePageHeading).toBeInTheDocument();
});
