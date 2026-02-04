import React, { useState, useMemo } from 'react';

const getStatusColor = (status) => {
    switch (status) {
        case 'connected': return 'green';
        case 'linking':
        case 'connecting':
        case 'initializing':
        case 'got qr code':
        case 'waiting': return 'orange';
        case 'disconnected':
        case 'invalid_config': return 'gray';
        default: return 'gray';
    }
};

const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '1.5rem',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    borderRadius: '8px',
    overflow: 'hidden'
};

const thStyle = {
    backgroundColor: '#f8f9fa',
    color: '#495057',
    fontWeight: '600',
    padding: '12px 15px',
    textAlign: 'left',
    borderBottom: '2px solid #dee2e6',
    cursor: 'pointer', // Make headers clickable
    userSelect: 'none'
};

const tdStyle = {
    padding: '12px 15px',
    borderBottom: '1px solid #dee2e6',
    verticalAlign: 'middle',
    textAlign: 'left'
};

const filterInputStyle = {
    width: '100%',
    padding: '4px 8px',
    marginTop: '5px',
    borderRadius: '4px',
    border: '1px solid #ced4da',
    fontSize: '0.85rem',
    boxSizing: 'border-box'
};

function UserTable({ configs, selectedUserId, onSelectUser, enableFiltering = false, showOwnerColumn = true }) {
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'ascending' });
    const [filters, setFilters] = useState({});

    // Handle Sort Click
    const requestSort = (key) => {
        let direction = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') {
            direction = 'descending';
        }
        setSortConfig({ key, direction });
    };

    // Handle Filter Change
    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    // Process Data (Filter then Sort)
    const processedConfigs = useMemo(() => {
        let items = [...configs];

        // 1. Filtering
        if (enableFiltering) {
            items = items.filter(item => {
                for (let key in filters) {
                    if (filters[key]) {
                        let itemValue = item[key];

                        // Map boolean/specific fields to their display representation for filtering
                        if (key === 'authenticated') {
                            itemValue = itemValue ? 'yes' : 'no';
                        }

                        const stringValue = String(itemValue || '').toLowerCase();
                        const filterValue = filters[key].toLowerCase();
                        if (!stringValue.includes(filterValue)) return false;
                    }
                }
                return true;
            });
        }

        // 2. Sorting
        if (sortConfig.key) {
            items.sort((a, b) => {
                let aValue = a[sortConfig.key] || '';
                let bValue = b[sortConfig.key] || '';

                // Special handling for status to group by color/meaning if needed, but simple string sort is usually fine
                // Special handling for boolean 'authenticated'
                if (sortConfig.key === 'authenticated') {
                    aValue = aValue ? 'yes' : 'no';
                    bValue = bValue ? 'yes' : 'no';
                }

                if (aValue < bValue) {
                    return sortConfig.direction === 'ascending' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'ascending' ? 1 : -1;
                }
                return 0;
            });
        }
        return items;
    }, [configs, sortConfig, filters, enableFiltering]);


    const getTrStyle = (userId) => ({
        backgroundColor: selectedUserId === userId ? '#e9ecef' : '#fff',
        cursor: 'pointer',
        transition: 'background-color 0.2s'
    });

    // Estimate row height (approx 60px) and header height (approx 50px) to stabilize layout
    const ROW_HEIGHT = 60;
    const HEADER_HEIGHT = 50;

    // Calculate target height based on TOTAL configs (unfiltered), capped at 80vh
    // This prevents the table from shrinking when filtering
    const [containerHeight, setContainerHeight] = useState('auto');

    React.useEffect(() => {
        const updateHeight = () => {
            const viewportHeight = window.innerHeight;
            // Reserve space for Headers, Buttons, Padding, Margins (approx 340px)
            // Layout analysis: 80px (page margins) + 64px (cards pad) + 50px (h2) + 110px (buttons area) ~= 304px
            // Setting reservation to 340px provides a safe buffer to prevent window scrollbar.
            const maxAllowed = Math.max(200, viewportHeight - 340);
            const contentHeight = (configs.length * ROW_HEIGHT) + HEADER_HEIGHT;

            // If content is smaller than max, use content height. Otherwise use max (which triggers scroll).
            const target = Math.min(contentHeight, maxAllowed);
            setContainerHeight(`${target}px`);
        };

        updateHeight();
        window.addEventListener('resize', updateHeight);
        return () => window.removeEventListener('resize', updateHeight);
    }, [configs.length]);

    const renderSortArrow = (key) => {
        // Use a fixed-width span to prevent jitter when arrow changes
        const content = sortConfig.key === key
            ? (sortConfig.direction === 'ascending' ? '▲' : '▼')
            : '↕';

        return (
            <span style={{
                display: 'inline-block',
                width: '1.5em',
                textAlign: 'center',
                opacity: sortConfig.key === key ? 1 : 0.3
            }}>
                {content}
            </span>
        );
    };

    return (
        <div style={{
            overflowX: 'auto',
            height: containerHeight, // Fixed height logic
            overflowY: 'auto',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            backgroundColor: '#fff' // Ensure background is white
        }}>
            <table style={{ ...tableStyle, marginTop: 0, boxShadow: 'none', borderRadius: 0 }}>
                <thead style={{ position: 'sticky', top: 0, zIndex: 1, backgroundColor: '#f8f9fa' }}>
                    <tr>
                        <th style={thStyle} onClick={() => requestSort('user_id')}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                User Name {renderSortArrow('user_id')}
                            </div>
                            {enableFiltering && (
                                <input
                                    type="text"
                                    style={filterInputStyle}
                                    placeholder="Filter..."
                                    value={filters.user_id || ''}
                                    onChange={(e) => handleFilterChange('user_id', e.target.value)}
                                    onClick={(e) => e.stopPropagation()} // Prevent sort trigger
                                />
                            )}
                        </th>

                        {showOwnerColumn && (
                            <th style={thStyle} onClick={() => requestSort('owner')}>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    Owner {renderSortArrow('owner')}
                                </div>
                                {enableFiltering && (
                                    <input
                                        type="text"
                                        style={filterInputStyle}
                                        placeholder="Filter..."
                                        value={filters.owner || ''}
                                        onChange={(e) => handleFilterChange('owner', e.target.value)}
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                )}
                            </th>
                        )}

                        <th style={thStyle} onClick={() => requestSort('authenticated')}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                Authenticated {renderSortArrow('authenticated')}
                            </div>
                            {enableFiltering && (
                                <input
                                    type="text"
                                    style={filterInputStyle}
                                    placeholder="Filter..."
                                    value={filters.authenticated || ''}
                                    onChange={(e) => handleFilterChange('authenticated', e.target.value)}
                                    onClick={(e) => e.stopPropagation()}
                                />
                            )}
                        </th>
                        <th style={thStyle} onClick={() => requestSort('status')}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                Linked {renderSortArrow('status')}
                            </div>
                            {enableFiltering && (
                                <input
                                    type="text"
                                    style={filterInputStyle}
                                    placeholder="Filter..."
                                    value={filters.status || ''}
                                    onChange={(e) => handleFilterChange('status', e.target.value)}
                                    onClick={(e) => e.stopPropagation()}
                                />
                            )}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {processedConfigs.length === 0 ? (
                        <tr>
                            <td colSpan={showOwnerColumn ? 4 : 3} style={{ ...tdStyle, textAlign: 'center', color: '#6c757d' }}>No configurations found.</td>
                        </tr>
                    ) : (
                        processedConfigs.map(config => (
                            <tr
                                key={config.user_id}
                                style={getTrStyle(config.user_id)}
                                onClick={() => onSelectUser(config.user_id)}
                            >
                                <td style={tdStyle}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        {config.user_id}
                                    </div>
                                </td>
                                {showOwnerColumn && (
                                    <td style={tdStyle}>
                                        {config.owner || '-'}
                                    </td>
                                )}
                                <td style={tdStyle}>
                                    {config.authenticated ? (
                                        <span style={{ color: 'green', fontWeight: 'bold' }}>Yes</span>
                                    ) : (
                                        <span style={{ color: '#6c757d' }}>No</span>
                                    )}
                                </td>
                                <td style={tdStyle}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span
                                            style={{
                                                height: '10px',
                                                width: '10px',
                                                backgroundColor: getStatusColor(config.status),
                                                borderRadius: '50%',
                                                display: 'inline-block'
                                            }}></span>
                                        {config.status}
                                    </div>
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
}

export default UserTable;
