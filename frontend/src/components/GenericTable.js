import React, { useState, useMemo } from 'react';

const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '1.5rem',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    borderRadius: '8px',
    tableLayout: 'fixed' // Prevent jitter
};

const thStyle = {
    backgroundColor: '#f8f9fa',
    color: '#495057',
    fontWeight: '600',
    padding: '12px 15px',
    textAlign: 'left',
    borderBottom: '2px solid #dee2e6',
    cursor: 'pointer', // Make headers clickable
    userSelect: 'none',
    position: 'sticky',
    top: 0,
    zIndex: 1
};

const tdStyle = {
    padding: '12px 15px',
    borderBottom: '1px solid #dee2e6',
    verticalAlign: 'middle',
    textAlign: 'left',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
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

/**
 * GenericTable Component
 * 
 * @param {Array} data - Array of data objects
 * @param {Array} columns - Array of column definitions:
 *   {
 *     key: string,        // Property name in data object
 *     label: string,      // Header label
 *     sortable?: boolean, // Enable sorting
 *     filterable?: boolean, // Enable filtering
 *     render?: (item) => ReactNode // Custom render function
 *   }
 * @param {string} idField - Unique identifier field name (default: 'id')
 * @param {string|number} selectedId - Currently selected item ID
 * @param {function} onSelect - Callback when item is selected
 * @param {boolean} enableFiltering - Global enable filtering toggle
 */
function GenericTable({
    data,
    columns,
    idField = 'id',
    selectedId,
    onSelect,
    enableFiltering = false,
    darkMode = false,
    compact = false, // Default to false
    style = {}
}) {
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
    const processedData = useMemo(() => {
        let items = [...data];

        // 1. Filtering
        if (enableFiltering) {
            items = items.filter(item => {
                for (let key in filters) {
                    if (filters[key]) {
                        const column = columns.find(c => c.key === key);
                        if (!column || !column.filterable) continue;

                        let itemValue = column.getValue ? column.getValue(item) : item[key];

                        const stringValue = String(itemValue || '').toLowerCase();
                        const filterValue = filters[key].toLowerCase();

                        // EMERGENCY FIX: Force status to be startsWith
                        if (key === 'status') {
                            if (!stringValue.startsWith(filterValue)) return false;
                            continue;
                        }

                        // Check filter type
                        if (column.customFilter) {
                            if (!column.customFilter(stringValue, filterValue, item)) return false;
                        } else if (column.filterType === 'startsWith') {
                            if (!stringValue.startsWith(filterValue)) return false;
                        } else {
                            if (!stringValue.includes(filterValue)) return false;
                        }
                    }
                }
                return true;
            });
        }

        // 2. Sorting
        if (sortConfig.key) {
            const column = columns.find(c => c.key === sortConfig.key);
            items.sort((a, b) => {
                let aValue = column && column.getValue ? column.getValue(a) : (a[sortConfig.key] || '');
                let bValue = column && column.getValue ? column.getValue(b) : (b[sortConfig.key] || '');

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
    }, [data, sortConfig, filters, enableFiltering, columns]);


    // Dynamic styles based on darkMode
    const dynamicTableStyle = {
        ...tableStyle,
        boxShadow: darkMode ? '0 4px 12px rgba(0,0,0,0.3)' : '0 4px 6px rgba(0,0,0,0.1)',
    };

    const dynamicThStyle = {
        ...thStyle,
        backgroundColor: darkMode ? 'rgba(30, 41, 59, 0.9)' : '#f8f9fa',
        color: darkMode ? '#e2e8f0' : '#495057',
        borderBottom: darkMode ? '2px solid rgba(129, 140, 248, 0.3)' : '2px solid #dee2e6',
    };

    const dynamicTdStyle = {
        ...tdStyle,
        borderBottom: darkMode ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid #dee2e6',
        color: darkMode ? '#e2e8f0' : 'inherit',
    };

    const dynamicFilterInputStyle = {
        ...filterInputStyle,
        backgroundColor: darkMode ? 'rgba(15, 23, 42, 0.6)' : '#fff',
        border: darkMode ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid #ced4da',
        color: darkMode ? '#f8fafc' : 'inherit',
    };

    const getTrStyle = (itemId) => ({
        backgroundColor: selectedId === itemId
            ? (darkMode ? 'rgba(99, 102, 241, 0.3)' : '#e9ecef')
            : (darkMode ? 'transparent' : '#fff'),
        cursor: 'pointer',
        transition: 'background-color 0.2s'
    });

    const ROW_HEIGHT = compact ? 40 : 60;
    const HEADER_HEIGHT = compact ? 40 : 50;
    const [containerHeight, setContainerHeight] = useState('auto');

    // Dynamic Styles for Compact Mode
    // ----------------------------
    const activeTdStyle = {
        ...dynamicTdStyle,
        padding: compact ? '6px 12px' : '12px 15px',
        fontSize: compact ? '0.9rem' : 'inherit'
    };

    const activeThStyle = {
        ...dynamicThStyle,
        padding: compact ? '8px 12px' : '12px 15px',
        fontSize: compact ? '0.9rem' : 'inherit'
    };
    // ----------------------------

    React.useEffect(() => {
        const updateHeight = () => {
            const viewportHeight = window.innerHeight;
            // Adjust maxAllowed slightly since header is now outside this calculation
            // Was (viewport - 340), now maybe (viewport - 340 - HEADER_HEIGHT)?
            // Actually, keep it simple. Body max height.
            const maxAllowed = Math.max(200, viewportHeight - 400);
            const contentHeight = (data.length * ROW_HEIGHT);
            const target = Math.min(contentHeight, maxAllowed);
            setContainerHeight(`${target}px`);
        };

        updateHeight();
        window.addEventListener('resize', updateHeight);
        return () => window.removeEventListener('resize', updateHeight);
    }, [data.length, compact]);

    const renderSortArrow = (key) => {
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

    const renderColGroup = () => (
        <colgroup>
            {columns.map(col => (
                <col key={col.key} style={{ width: col.width }} />
            ))}
        </colgroup>
    );

    // Use flexbox for height management
    const containerStyle = {
        border: darkMode ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid #dee2e6',
        borderRadius: '0.75rem',
        backgroundColor: darkMode ? 'rgba(15, 23, 42, 0.4)' : '#fff',
        marginTop: '1.5rem',
        boxShadow: darkMode ? '0 4px 12px rgba(0,0,0,0.3)' : '0 4px 6px rgba(0,0,0,0.1)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        flex: 1, // Take remaining space
        minHeight: compact ? '200px' : '350px', // Reduced minimum in compact mode
        ...style
    };

    return (
        <div style={containerStyle}>
            {/* Header Section */}
            <div style={{
                flex: '0 0 auto', // Don't shrink or grow
                overflow: 'hidden',
                scrollbarGutter: 'stable',
                backgroundColor: darkMode ? 'rgba(30, 41, 59, 0.9)' : '#f8f9fa',
                borderBottom: darkMode ? '1px solid rgba(129, 140, 248, 0.3)' : '1px solid #dee2e6'
            }}>
                <table style={{ ...dynamicTableStyle, marginTop: 0, marginBottom: 0, boxShadow: 'none', borderRadius: 0 }}>
                    {renderColGroup()}
                    <thead style={{ backgroundColor: darkMode ? 'rgba(30, 41, 59, 0.9)' : '#f8f9fa' }}>
                        <tr>
                            {columns.map(col => (
                                <th
                                    key={col.key}
                                    style={{ ...activeThStyle }}
                                    onClick={() => col.sortable && requestSort(col.key)}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center' }}>
                                        {col.label} {col.sortable && renderSortArrow(col.key)}
                                    </div>
                                    {enableFiltering && col.filterable && (
                                        <input
                                            type="text"
                                            style={dynamicFilterInputStyle}
                                            placeholder={`Filter ${col.label}...`}
                                            value={filters[col.key] || ''}
                                            onChange={(e) => handleFilterChange(col.key, e.target.value)}
                                            onClick={(e) => e.stopPropagation()}
                                        />
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                </table>
            </div>

            {/* Body Section */}
            <div style={{
                flex: '1 1 auto', // Grow and shrink
                overflowX: 'auto',
                overflowY: 'auto',
                scrollbarGutter: 'stable',
                // Removed fixed height calculation
            }}>
                <table style={{ ...dynamicTableStyle, marginTop: 0, boxShadow: 'none', borderRadius: 0, borderTop: 'none' }}>
                    {renderColGroup()}
                    <tbody>
                        {processedData.length === 0 ? (
                            <tr>
                                <td colSpan={columns.length} style={{ ...activeTdStyle, textAlign: 'center', color: darkMode ? '#94a3b8' : '#6c757d' }}>
                                    No items found.
                                </td>
                            </tr>
                        ) : (
                            processedData.map(item => (
                                <tr
                                    key={item[idField]}
                                    style={getTrStyle(item[idField])}
                                    onClick={() => onSelect(item[idField])}
                                >
                                    {columns.map(col => (
                                        <td key={`${item[idField]}-${col.key}`} style={activeTdStyle}>
                                            {col.render ? col.render(item) : (item[col.key] || '-')}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default GenericTable;
