import React from 'react';
import PhoneInput from 'react-phone-number-input';
import 'react-phone-number-input/style.css';
import './PhoneInputWidget.css'; // Custom styles to match theme

const PhoneInputWidget = ({ value, onChange, disabled }) => {
    return (
        <PhoneInput
            international
            defaultCountry="IL" // Default to IL as requested by user context (Moshe/IL example)
            value={value}
            onChange={onChange}
            disabled={disabled}
            className="custom-phone-input"
        />
    );
};

export default PhoneInputWidget;
