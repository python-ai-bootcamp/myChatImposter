
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import CronPickerWidget from './CronPickerWidget';

describe('CronPickerWidget', () => {

    test('renders summary text correctly for daily cron', () => {
        render(<CronPickerWidget value="30 08 * * *" onChange={() => { }} />);
        expect(screen.getByText('Daily at 08:30')).toBeInTheDocument();
    });

    test('renders summary text correctly for weekly cron', () => {
        render(<CronPickerWidget value="00 09 * * 1,3" onChange={() => { }} />);
        expect(screen.getByText('Weekly on Mon, Wed at 09:00')).toBeInTheDocument();
    });

    test('renders raw cron string for custom/complex cron', () => {
        render(<CronPickerWidget value="*/15 * * * *" onChange={() => { }} />);
        expect(screen.getByText('*/15 * * * *')).toBeInTheDocument();
    });

    test('opens modal when Schedule button is clicked', () => {
        render(<CronPickerWidget value="" onChange={() => { }} />);
        fireEvent.click(screen.getByText('Schedule'));
        expect(screen.getByText('Configure Schedule')).toBeInTheDocument();
    });

    test('parses daily cron and populates form in modal', () => {
        render(<CronPickerWidget value="45 23 * * *" onChange={() => { }} />);
        fireEvent.click(screen.getByText('Schedule'));

        // Should be on Daily tab
        // We check for the Daily-specific text
        expect(screen.getByText('Trigger the message collection once every day at this time.')).toBeInTheDocument();

        // Check time input value
        const timeInput = screen.getByDisplayValue('23:45');
        expect(timeInput).toBeInTheDocument();
    });

    test('parses weekly cron and populates form in modal', () => {
        // Mon (1) and Fri (5) at 14:00
        render(<CronPickerWidget value="00 14 * * 1,5" onChange={() => { }} />);
        fireEvent.click(screen.getByText('Schedule'));

        // Should detect Weekly tab (check for Days of Week label)
        expect(screen.getByText('Days of Week')).toBeInTheDocument();

        // Check time input
        expect(screen.getByDisplayValue('14:00')).toBeInTheDocument();

        // Check checkboxes
        const monCheckbox = screen.getByLabelText('Mon');
        const friCheckbox = screen.getByLabelText('Fri');
        const sunCheckbox = screen.getByLabelText('Sun');

        expect(monCheckbox).toBeChecked();
        expect(friCheckbox).toBeChecked();
        expect(sunCheckbox).not.toBeChecked();
    });

    test('parses custom cron and populates form in modal', () => {
        render(<CronPickerWidget value="*/5 * * * *" onChange={() => { }} />);
        fireEvent.click(screen.getByText('Schedule'));

        // Should be on Custom tab
        expect(screen.getByText('Cron Expression')).toBeInTheDocument();
        expect(screen.getByDisplayValue('*/5 * * * *')).toBeInTheDocument();
    });

    test('generates correct daily cron on save', () => {
        const handleChange = jest.fn();
        render(<CronPickerWidget value="00 09 * * *" onChange={handleChange} />);

        fireEvent.click(screen.getByText('Schedule'));

        // Change time to 10:30
        const timeInput = screen.getByDisplayValue('09:00');
        fireEvent.change(timeInput, { target: { value: '10:30' } });

        fireEvent.click(screen.getByText('Save'));

        expect(handleChange).toHaveBeenCalledWith('30 10 * * *');
    });

    test('generates correct weekly cron on save', () => {
        const handleChange = jest.fn();
        // Start with Mon (1) at 09:00
        render(<CronPickerWidget value="00 09 * * 1" onChange={handleChange} />);

        fireEvent.click(screen.getByText('Schedule'));

        // Toggle Mon off, Tue on
        fireEvent.click(screen.getByLabelText('Mon')); // Mon off
        fireEvent.click(screen.getByLabelText('Tue')); // Tue on

        fireEvent.click(screen.getByText('Save'));

        // Should be Tue (2) at 09:00
        expect(handleChange).toHaveBeenCalledWith('0 9 * * 2'); // Note: Integers usually parsed as decimal
    });

    test('handles switching tabs correctly', () => {
        const handleChange = jest.fn();
        render(<CronPickerWidget value="00 09 * * *" onChange={handleChange} />);
        fireEvent.click(screen.getByText('Schedule'));

        // Switch to Custom
        fireEvent.click(screen.getByText('Custom'));
        expect(screen.getByPlaceholderText('* * * * *')).toBeInTheDocument();

        // Type custom cron
        fireEvent.change(screen.getByPlaceholderText('* * * * *'), { target: { value: '1 2 3 4 5' } });

        fireEvent.click(screen.getByText('Save'));
        expect(handleChange).toHaveBeenCalledWith('1 2 3 4 5');
    });

    test('closes modal on Cancel', () => {
        render(<CronPickerWidget value="" onChange={() => { }} />);
        fireEvent.click(screen.getByText('Schedule'));
        expect(screen.getByText('Configure Schedule')).toBeInTheDocument();

        fireEvent.click(screen.getByText('Cancel'));
        expect(screen.queryByText('Configure Schedule')).not.toBeInTheDocument();
    });

});
