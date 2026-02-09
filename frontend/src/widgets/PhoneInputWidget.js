import React from 'react';
import PhoneInput from 'react-phone-number-input';
import flags from 'react-phone-number-input/flags';
import 'react-phone-number-input/style.css';
import './PhoneInputWidget.css'; // Custom styles to match theme

const PhoneInputWidget = ({ value, onChange, disabled, onKeyDown }) => {
    // Prevent Enter from submitting the form
    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
        }
        // Call parent handler if provided
        if (onKeyDown) {
            onKeyDown(e);
        }
    };

    return (
        <PhoneInput
            international
            defaultCountry="IL"
            value={value}
            onChange={onChange}
            disabled={disabled}
            flags={flags}
            className="custom-phone-input"
            onKeyDown={handleKeyDown}
        />
    );
};

export default PhoneInputWidget;
