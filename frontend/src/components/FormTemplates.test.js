
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
    CustomCheckboxWidget,
    NarrowTextWidget,
    SystemPromptWidget,
    TimezoneSelectWidget,
    LanguageSelectWidget,
    InlineCheckboxFieldTemplate
} from './FormTemplates';

// Mock fetch
global.fetch = jest.fn();

describe('FormTemplates Widgets', () => {

    beforeEach(() => {
        fetch.mockClear();
    });

    // --- Simple Widgets ---

    test('CustomCheckboxWidget renders and handles change', () => {
        const handleChange = jest.fn();
        render(<CustomCheckboxWidget id="test-id" value={false} onChange={handleChange} required={false} />);

        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).not.toBeChecked();

        fireEvent.click(checkbox);
        expect(handleChange).toHaveBeenCalledWith(true);
    });

    test('NarrowTextWidget renders and handles change', () => {
        const handleChange = jest.fn();
        render(<NarrowTextWidget id="test-text" value="initial" onChange={handleChange} />);

        const input = screen.getByRole('textbox');
        expect(input).toHaveValue('initial');
        expect(input).toHaveStyle({ width: '80px' });

        fireEvent.change(input, { target: { value: 'updated' } });
        expect(handleChange).toHaveBeenCalledWith('updated');
    });

    test('SystemPromptWidget renders correct dimensions', () => {
        render(<SystemPromptWidget id="prompt" value="" onChange={() => { }} />);
        const area = screen.getByRole('textbox');
        expect(area).toHaveStyle({ width: '290px', height: '150px' });
    });

    test('InlineCheckboxFieldTemplate renders label and children', () => {
        render(
            <InlineCheckboxFieldTemplate id="test-check" label="Test Label" required={true}>
                <input type="checkbox" data-testid="child-check" />
            </InlineCheckboxFieldTemplate>
        );
        expect(screen.getByText('Test Label*')).toBeInTheDocument();
        expect(screen.getByTestId('child-check')).toBeInTheDocument();
    });

    // --- Complex Widgets ---

    describe('TimezoneSelectWidget', () => {

        test('renders current value and opens dropdown', () => {
            render(<TimezoneSelectWidget value="UTC" onChange={() => { }} />);

            // Should show selected value (and offset)
            expect(screen.getByText(/UTC/)).toBeInTheDocument();

            // Click to open
            fireEvent.click(screen.getByText(/UTC/));

            // Dropdown should appear with filter input
            expect(screen.getByPlaceholderText('Filter...')).toBeInTheDocument();

            // Should list options
            expect(screen.getByText('Europe/London')).toBeInTheDocument();
        });

        test('filters options', () => {
            render(<TimezoneSelectWidget value="" onChange={() => { }} />);
            fireEvent.click(screen.getByText('Select timezone...'));

            const filterInput = screen.getByPlaceholderText('Filter...');
            fireEvent.change(filterInput, { target: { value: 'New_York' } });

            // Should show New York
            expect(screen.getByText('America/New York')).toBeInTheDocument();
            // Should NOT show London
            expect(screen.queryByText('Europe/London')).not.toBeInTheDocument();
        });

        test('calls onChange when option selected', () => {
            const handleChange = jest.fn();
            render(<TimezoneSelectWidget value="" onChange={handleChange} />);
            fireEvent.click(screen.getByText('Select timezone...'));

            fireEvent.click(screen.getByText('Europe/Paris'));

            expect(handleChange).toHaveBeenCalledWith('Europe/Paris');
        });
    });

    describe('LanguageSelectWidget', () => {

        const mockLanguages = [
            { code: 'en', name: 'English', native_name: 'English' },
            { code: 'es', name: 'Spanish', native_name: 'Español' },
            { code: 'fr', name: 'French', native_name: 'Français' }
        ];

        test('fetches languages and renders dropdown', async () => {
            fetch.mockResolvedValueOnce({
                json: async () => mockLanguages
            });

            await act(async () => {
                render(<LanguageSelectWidget value={'en'} onChange={() => { }} />);
            });

            // Expect fetch call
            expect(fetch).toHaveBeenCalledWith('/api/resources/languages');

            // Wait for text to appear (handling async render)
            expect(await screen.findByText('English (English)')).toBeInTheDocument();

            // Open dropdown
            fireEvent.click(screen.getByText('English (English)'));

            // Check options
            expect(screen.getByText('Spanish (Español)')).toBeInTheDocument();
        });

        test('handles fetch failure gracefully', async () => {
            const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
            fetch.mockRejectedValueOnce(new Error('API Fail'));

            await act(async () => {
                render(<LanguageSelectWidget value="" onChange={() => { }} />);
            });

            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();

            // Should still render placeholder
            expect(screen.getByText('Select language...')).toBeInTheDocument();
        });
    });

});
