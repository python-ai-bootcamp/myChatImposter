import React from 'react';

// Filterable language dropdown widget - fetches from API
export function LanguageSelectWidget(props) {
    const [isOpen, setIsOpen] = React.useState(false);
    const [filter, setFilter] = React.useState('');
    const [languages, setLanguages] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const containerRef = React.useRef(null);

    // Fetch languages from API on mount
    React.useEffect(() => {
        fetch('/api/external/resources/languages')
            .then(res => res.json())
            .then(data => {
                setLanguages(data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to fetch languages:', err);
                setLoading(false);
            });
    }, []);

    // Build language options from API data
    const languageOptions = React.useMemo(() => {
        return languages.map(lang => ({
            value: lang.code,
            label: `${lang.name} (${lang.native_name})`,
            code: lang.code.toUpperCase()
        })).sort((a, b) => a.label.localeCompare(b.label));
    }, [languages]);

    // Filter options based on input
    const filteredOptions = React.useMemo(() => {
        if (!filter) return languageOptions;
        const lowerFilter = filter.toLowerCase();
        return languageOptions.filter(opt =>
            opt.label.toLowerCase().includes(lowerFilter) ||
            opt.value.toLowerCase().includes(lowerFilter)
        );
    }, [filter, languageOptions]);

    // Get display text for current value
    const currentOption = languageOptions.find(opt => opt.value === props.value);
    const displayText = currentOption
        ? currentOption.label
        : loading ? 'Loading...' : (props.value || 'Select language...');

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

    const handleSelect = (value) => {
        props.onChange(value);
        setIsOpen(false);
        setFilter('');
    };

    return (
        <div ref={containerRef} style={{ position: 'relative', display: 'inline-block', width: '250px' }}>
            <div
                onClick={() => !loading && setIsOpen(!isOpen)}
                style={{
                    padding: '4px 8px',
                    border: '1px solid #ccc',
                    borderRadius: '3px',
                    cursor: loading ? 'wait' : 'pointer',
                    backgroundColor: '#fff',
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
                    border: '1px solid #ccc',
                    borderRadius: '3px',
                    backgroundColor: '#fff',
                    zIndex: 1000,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
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
                            borderBottom: '1px solid #eee',
                            outline: 'none',
                            width: '100%',
                            boxSizing: 'border-box'
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
                                    backgroundColor: opt.value === props.value ? '#e6f7ff' : 'transparent',
                                    display: 'flex',
                                    justifyContent: 'space-between'
                                }}
                                onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                                onMouseLeave={(e) => e.target.style.backgroundColor = opt.value === props.value ? '#e6f7ff' : 'transparent'}
                            >
                                <span>{opt.label}</span>
                                <span style={{ color: '#888', fontSize: '0.9em' }}>{opt.code}</span>
                            </div>
                        ))}
                        {filteredOptions.length === 0 && (
                            <div style={{ padding: '8px', color: '#888', textAlign: 'center' }}>No matches</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
