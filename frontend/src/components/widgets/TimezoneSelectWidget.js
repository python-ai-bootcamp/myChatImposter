import React from 'react';

// Get UTC offset string for a timezone (e.g., "+02:00", "-05:00")
function getTimezoneOffset(timezone) {
    try {
        const now = new Date();
        const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: timezone,
            timeZoneName: 'shortOffset'
        });
        const parts = formatter.formatToParts(now);
        const offsetPart = parts.find(p => p.type === 'timeZoneName');
        if (offsetPart) {
            // Convert "GMT+2" to "+02:00" format
            const value = offsetPart.value;
            if (value === 'GMT') return '+00:00';
            const match = value.match(/GMT([+-])(\d+)(?::(\d+))?/);
            if (match) {
                const sign = match[1];
                const hours = match[2].padStart(2, '0');
                const mins = match[3] || '00';
                return `${sign}${hours}:${mins}`;
            }
            return value.replace('GMT', '');
        }
    } catch (e) {
        return '';
    }
    return '';
}

// Filterable timezone dropdown widget
export function TimezoneSelectWidget(props) {
    const [isOpen, setIsOpen] = React.useState(false);
    const [filter, setFilter] = React.useState('');
    const [timezones, setTimezones] = React.useState([]);
    const containerRef = React.useRef(null);

    React.useEffect(() => {
        fetch('/api/external/resources/timezones')
            .then(res => {
                if (!res.ok) throw new Error('Network response was not ok');
                return res.json();
            })
            .then(data => setTimezones(data))
            .catch(err => console.error("Failed to fetch timezones:", err));
    }, []);

    // Build timezone options with offsets
    const timezoneOptions = React.useMemo(() => {
        return timezones.map(tz => ({
            value: tz,
            label: tz.replace(/_/g, ' '),
            offset: getTimezoneOffset(tz)
        })).sort((a, b) => {
            // Sort by offset, then alphabetically
            const offsetA = a.offset || '+00:00';
            const offsetB = b.offset || '+00:00';
            if (offsetA !== offsetB) return offsetA.localeCompare(offsetB);
            return a.label.localeCompare(b.label);
        });
    }, [timezones]);

    // Filter options based on input
    const filteredOptions = React.useMemo(() => {
        if (!filter) return timezoneOptions;
        const lowerFilter = filter.toLowerCase();
        return timezoneOptions.filter(opt =>
            opt.label.toLowerCase().includes(lowerFilter) ||
            opt.value.toLowerCase().includes(lowerFilter) ||
            opt.offset.includes(lowerFilter)
        );
    }, [filter, timezoneOptions]);

    // Get display text for current value
    const currentOption = timezoneOptions.find(opt => opt.value === props.value);
    const displayText = currentOption
        ? `${currentOption.label} (${currentOption.offset})`
        : props.value || 'Select timezone...';

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
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    padding: '4px 8px',
                    border: '1px solid #ccc',
                    borderRadius: '3px',
                    cursor: 'pointer',
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
                                <span style={{ color: '#888', fontSize: '0.9em' }}>{opt.offset}</span>
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
