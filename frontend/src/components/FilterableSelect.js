import React, { useState, useRef, useMemo } from 'react';
import SelectMenuPortal from './widgets/SelectMenuPortal';
import './widgets/CountrySelectWidget.css'; // Re-use the existing CSS for consistency

/**
 * A generic filterable dropdown select component.
 * Now styled to match CountrySelectWidget.
 * 
 * Props:
 * - value: The currently selected value.
 * - onChange: Callback when a value is selected.
 * - options: Array of { value, label, secondary (optional) }.
 * - placeholder: Placeholder text when no value is selected.
 * - loading: Boolean to indicate if options are loading.
 * - darkMode: Boolean for dark mode styling.
 */
function FilterableSelect({
    value,
    onChange,
    options = [],
    placeholder = 'Select...',
    loading = false,
    darkMode = false,
    error // New error prop
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const containerRef = useRef(null);

    // Filter options based on input
    const filteredOptions = useMemo(() => {
        if (!searchTerm) return options;
        const lowerFilter = searchTerm.toLowerCase();
        return options.filter(opt =>
            opt.label.toLowerCase().includes(lowerFilter) ||
            opt.value.toLowerCase().includes(lowerFilter) ||
            (opt.secondary && opt.secondary.toLowerCase().includes(lowerFilter))
        );
    }, [searchTerm, options]);

    // Find current option
    const currentOption = options.find(opt => opt.value === value);

    // Close logic is now handled by SelectMenuPortal for outside clicks in the menu,
    // but the input logic remains here.

    const handleSelect = (optValue) => {
        onChange(optValue);
        setIsOpen(false);
        setSearchTerm('');
    };

    const handleClear = (e) => {
        e.stopPropagation();
        onChange('');
        setSearchTerm('');
    };

    const handleInputClick = () => {
        if (!loading) {
            setIsOpen(true);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (filteredOptions.length > 0) {
                handleSelect(filteredOptions[0].value);
            }
        } else if (e.key === 'Escape') {
            setIsOpen(false);
            setSearchTerm('');
        }
    };

    const containerClass = `country-select-container ${darkMode ? 'dark' : ''} ${isOpen ? 'open' : ''} ${error ? 'has-error' : ''}`;

    return (
        <div ref={containerRef} className={containerClass} style={{ width: '100%' }} title={error || ''}>
            <div className="country-select-control" onClick={handleInputClick}>
                <div className="country-select-value">
                    {isOpen ? (
                        <input
                            type="text"
                            className="country-select-input"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={currentOption ? currentOption.label : placeholder}
                            autoFocus
                        />
                    ) : (
                        <span className="country-select-display">
                            {loading ? 'Loading...' : (currentOption ? `${currentOption.label} ${currentOption.secondary ? `(${currentOption.secondary})` : ''}` : placeholder)}
                        </span>
                    )}
                </div>

                {/* Clear button */}
                {value && !loading && (
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

            <SelectMenuPortal
                isOpen={isOpen}
                anchorRef={containerRef}
                onClose={() => setIsOpen(false)}
            >
                <div className={`country-select-menu ${darkMode ? 'dark' : ''}`} style={{ position: 'static', marginTop: 0, width: '100%', boxSizing: 'border-box' }}>
                    {filteredOptions.length === 0 ? (
                        <div className={`country-select-no-options ${darkMode ? 'dark' : ''}`}>No matches found</div>
                    ) : (
                        filteredOptions.map(opt => (
                            <div
                                key={opt.value}
                                className={`country-select-option ${opt.value === value ? 'selected' : ''} ${darkMode ? 'dark' : ''}`}
                                onClick={() => handleSelect(opt.value)}
                            >
                                <span className="country-name">{opt.label}</span>
                                {opt.secondary && <span style={{ opacity: 0.6, fontSize: '0.85em', marginLeft: 'auto' }}>{opt.secondary}</span>}
                            </div>
                        ))
                    )}
                </div>
            </SelectMenuPortal>
        </div>
    );
}

export default FilterableSelect;
