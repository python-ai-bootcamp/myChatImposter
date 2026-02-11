import React from 'react';

/**
 * A generic filterable dropdown select component.
 * 
 * Props:
 * - value: The currently selected value.
 * - onChange: Callback when a value is selected.
 * - options: Array of { value, label, secondary (optional) }.
 * - placeholder: Placeholder text when no value is selected.
 * - loading: Boolean to indicate if options are loading.
 * - width: Optional width (default 250px).
 */
function FilterableSelect({
    value,
    onChange,
    options = [],
    placeholder = 'Select...',
    loading = false,
    width = '250px'
}) {
    const [isOpen, setIsOpen] = React.useState(false);
    const [filter, setFilter] = React.useState('');
    const containerRef = React.useRef(null);

    // Filter options based on input
    const filteredOptions = React.useMemo(() => {
        if (!filter) return options;
        const lowerFilter = filter.toLowerCase();
        return options.filter(opt =>
            opt.label.toLowerCase().includes(lowerFilter) ||
            opt.value.toLowerCase().includes(lowerFilter) ||
            (opt.secondary && opt.secondary.toLowerCase().includes(lowerFilter))
        );
    }, [filter, options]);

    // Get display text for current value
    const currentOption = options.find(opt => opt.value === value);
    const displayText = currentOption
        ? (currentOption.secondary ? `${currentOption.label} (${currentOption.secondary})` : currentOption.label)
        : loading ? 'Loading...' : placeholder;

    // Close dropdown when clicking outside
    React.useEffect(() => {
        const handleClickOutside = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelect = (optValue) => {
        onChange(optValue);
        setIsOpen(false);
        setFilter('');
    };

    return (
        <div ref={containerRef} style={{ position: 'relative', display: 'inline-block', width }}>
            <div
                onClick={() => !loading && setIsOpen(!isOpen)}
                style={{
                    padding: '4px 8px',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '3px',
                    cursor: loading ? 'wait' : 'pointer',
                    backgroundColor: 'rgba(15, 23, 42, 0.6)',
                    color: '#e2e8f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}
            >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {displayText}
                </span>
                <span style={{ marginLeft: '8px' }}>{isOpen ? '▲' : '▼'}</span>
            </div>

            {isOpen && (
                <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '3px',
                    backgroundColor: '#1e293b',
                    zIndex: 1000,
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
                    maxHeight: '250px',
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    <input
                        type="text"
                        placeholder="Filter..."
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                            padding: '6px 8px',
                            border: 'none',
                            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                            outline: 'none',
                            width: '100%',
                            boxSizing: 'border-box',
                            backgroundColor: 'rgba(15, 23, 42, 0.6)',
                            color: '#e2e8f0'
                        }}
                        autoFocus
                    />
                    <div style={{ overflowY: 'auto', maxHeight: '200px' }}>
                        {filteredOptions.map(opt => (
                            <div
                                key={opt.value}
                                onClick={() => handleSelect(opt.value)}
                                style={{
                                    padding: '6px 8px',
                                    cursor: 'pointer',
                                    backgroundColor: opt.value === value ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                                    color: '#e2e8f0',
                                    display: 'flex',
                                    justifyContent: 'space-between'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#334155'}
                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = opt.value === value ? 'rgba(99, 102, 241, 0.3)' : 'transparent'}
                            >
                                <span>{opt.label}</span>
                                {opt.secondary && <span style={{ color: '#94a3b8', fontSize: '0.9em' }}>{opt.secondary}</span>}
                            </div>
                        ))}
                        {filteredOptions.length === 0 && (
                            <div style={{ padding: '8px', color: '#94a3b8', textAlign: 'center' }}>No matches</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default FilterableSelect;
