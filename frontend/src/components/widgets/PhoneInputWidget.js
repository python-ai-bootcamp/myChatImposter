import React from 'react';
import PhoneInput from 'react-phone-number-input';
import flags from 'react-phone-number-input/flags';
import 'react-phone-number-input/style.css';
import './PhoneInputWidget.css'; // Custom styles to match theme

const PhoneInputWidget = ({ value, onChange, disabled, onKeyDown, error }) => {
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
        <div title={error || ''} style={{ width: '100%' }}>
            <PhoneInput
                international
                defaultCountry="IL"
                value={value}
                onChange={onChange}
                disabled={disabled}
                flags={flags}
                className={`custom-phone-input ${error ? 'has-error' : ''}`}
                onKeyDown={handleKeyDown}
            />
        </div>
    );
};

export default PhoneInputWidget;
