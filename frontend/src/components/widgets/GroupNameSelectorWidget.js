import React from 'react';

// Group Name Selector Widget - uses formContext to access state
export const GroupNameSelectorWidget = (props) => {
    const { availableGroups, isLinked, formData, setFormData } = props.formContext || {};
    const [inputValue, setInputValue] = React.useState(props.value || '');
    const [isMenuOpen, setIsMenuOpen] = React.useState(false);
    const isFocusedRef = React.useRef(false);

    // Only sync from props when not focused (external changes like JSON editor)
    React.useEffect(() => {
        if (!isFocusedRef.current) {
            setInputValue(props.value || '');
        }
    }, [props.value]);

    const groups = availableGroups || [];

    const filteredGroups = groups.filter(g =>
        (g.subject || '').toLowerCase().includes((inputValue || '').toLowerCase())
    );

    const handleInputChange = (e) => {
        setInputValue(e.target.value);
        setIsMenuOpen(true);
        props.onChange(e.target.value);
    };

    const handleFocus = () => {
        isFocusedRef.current = true;
        setIsMenuOpen(true);
    };

    const handleBlur = () => {
        isFocusedRef.current = false;
        setTimeout(() => setIsMenuOpen(false), 200);
    };

    const handleSelect = (group) => {
        setInputValue(group.subject);
        setIsMenuOpen(false);

        // Extract the array index from the widget's id
        // New path: root_features_periodic_group_tracking_tracked_groups_0_displayName
        const idMatch = props.id.match(/tracked_groups_(\d+)_displayName$/);
        if (idMatch && formData && setFormData) {
            const idx = parseInt(idMatch[1], 10);
            const currentData = JSON.parse(JSON.stringify(formData));
            if (currentData?.features?.periodic_group_tracking?.tracked_groups?.[idx]) {
                currentData.features.periodic_group_tracking.tracked_groups[idx].groupIdentifier = group.id;
                currentData.features.periodic_group_tracking.tracked_groups[idx].displayName = group.subject;
                setFormData(currentData);
            }
        }
    };

    if (!isLinked) {
        return (
            <input
                type="text"
                value={props.value || '(connect to select)'}
                disabled
                style={{
                    width: '150px',
                    backgroundColor: 'rgba(15, 23, 42, 0.4)', // Dark disabled background
                    color: '#64748b', // Slate-500 text
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '4px',
                    padding: '4px 8px'
                }}
                title="Adding or changing group details is prohibited for disconnected users"
            />
        );
    }

    return (
        <div style={{ position: 'relative' }}>
            <input
                type="text"
                placeholder="Type group name..."
                value={inputValue}
                onChange={handleInputChange}
                onFocus={handleFocus}
                onBlur={handleBlur}
                style={{
                    width: '150px',
                    padding: '4px 8px',
                    backgroundColor: 'rgba(15, 23, 42, 0.6)', // Dark input background
                    color: '#f8fafc', // Light text
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '4px'
                }}
            />
            {isMenuOpen && filteredGroups.length > 0 && (
                <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    width: '300px',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    backgroundColor: '#1e293b', // Dark dropdown background
                    zIndex: 1000,
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
                    borderRadius: '0.375rem'
                }}>
                    {filteredGroups.map(g => (
                        <div
                            key={g.id}
                            onMouseDown={() => handleSelect(g)}
                            style={{
                                padding: '8px',
                                cursor: 'pointer',
                                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                                color: '#f8fafc'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#334155'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                        >
                            <strong>{g.subject}</strong><br />
                            <small style={{ color: '#94a3b8' }}>{g.id}</small>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
