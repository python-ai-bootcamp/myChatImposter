import React, { useState, useEffect, useRef } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import SelectMenuPortal from './SelectMenuPortal';
import './CountrySelectWidget.css';

const CountrySelectWidget = ({ value, onChange, disabled, error, ...props }) => {
    const [countries, setCountries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef(null);

    useEffect(() => {
        fetch('/api/external/resources/countries')
            .then(res => res.json())
            .then(data => {
                setCountries(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load countries", err);
                setLoading(false);
            });
    }, []);

    // Find selected country object
    const selectedCountry = countries.find(c => c.code === value);

    // Filter countries based on search
    const filteredCountries = countries.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.code.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const handleSelect = (countryCode) => {
        onChange(countryCode);
        setIsOpen(false);
        setSearchTerm('');
    };

    const handleClear = (e) => {
        e.stopPropagation();
        onChange('');
        setSearchTerm('');
    };

    const handleInputChange = (e) => {
        setSearchTerm(e.target.value);
        if (!isOpen) setIsOpen(true);
    };

    const handleInputFocus = () => {
        setIsOpen(true);
    };

    // Removed blur handler because Portal click-outside handles closing now
    // If we keep blur, it might race with the portal click

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent form submission
            // Select the first matching option if available
            if (filteredCountries.length > 0) {
                handleSelect(filteredCountries[0].code);
            }
        } else if (e.key === 'Escape') {
            setIsOpen(false);
            setSearchTerm('');
        }
    };

    const { isDarkMode } = useTheme();
    const isDark = props.darkMode || isDarkMode;

    const containerClass = `country-select-container ${isDark ? 'dark' : ''} ${isOpen ? 'open' : ''} ${error ? 'has-error' : ''}`;

    return (
        <div className={containerClass} title={error || ''} ref={containerRef}>
            <div className="country-select-control" onClick={() => !disabled && setIsOpen(!isOpen)}>
                {/* Display selected value or search input */}
                <div className="country-select-value">
                    {isOpen ? (
                        <input
                            type="text"
                            className="country-select-input"
                            value={searchTerm}
                            onChange={handleInputChange}
                            onFocus={handleInputFocus}
                            onKeyDown={handleKeyDown}
                            placeholder={selectedCountry ? `${selectedCountry.flag} ${selectedCountry.name}` : "Select Country..."}
                            disabled={disabled}
                            autoFocus
                        />
                    ) : (
                        <span className="country-select-display">
                            {loading ? 'Loading...' : (selectedCountry ? `${selectedCountry.flag} ${selectedCountry.name}` : 'Select Country...')}
                        </span>
                    )}
                </div>

                {/* Clear button */}
                {value && !disabled && (
                    <button type="button" className="country-select-clear" onClick={handleClear}>
                        ×
                    </button>
                )}

                {/* Dropdown arrow */}
                <div className="country-select-arrow">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                        <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
                    </svg>
                </div>
            </div>

            {/* Dropdown menu via Portal */}
            <SelectMenuPortal
                isOpen={isOpen && !disabled}
                anchorRef={containerRef}
                onClose={() => setIsOpen(false)}
            >
                <div className={`country-select-menu ${isDark ? 'dark' : ''}`} style={{ position: 'static', marginTop: 0, width: '100%', boxSizing: 'border-box' }}>
                    {filteredCountries.length === 0 ? (
                        <div className={`country-select-no-options ${isDark ? 'dark' : ''}`}>No countries found</div>
                    ) : (
                        filteredCountries.map(country => (
                            <div
                                key={country.code}
                                className={`country-select-option ${country.code === value ? 'selected' : ''} ${isDark ? 'dark' : ''}`}
                                onClick={() => handleSelect(country.code)}
                            >
                                <span className="country-flag">{country.flag}</span>
                                <span className="country-name">{country.name}</span>
                            </div>
                        ))
                    )}
                </div>
            </SelectMenuPortal>
        </div>
    );
};

export default CountrySelectWidget;
