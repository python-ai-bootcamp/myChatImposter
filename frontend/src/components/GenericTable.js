import React, { useState, useMemo } from 'react';

const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '1.5rem',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    borderRadius: '8px'
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
    enableFiltering = false
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

                        let itemValue = item[key];
                        // If render function exists, we might need to filter on raw value or rendered?
                        // For simplicity, filter on raw value string properties

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


    const getTrStyle = (itemId) => ({
        backgroundColor: selectedId === itemId ? '#e9ecef' : '#fff',
        cursor: 'pointer',
        transition: 'background-color 0.2s'
    });

    const ROW_HEIGHT = 60;
    const HEADER_HEIGHT = 50;
    const [containerHeight, setContainerHeight] = useState('auto');

    React.useEffect(() => {
        const updateHeight = () => {
            const viewportHeight = window.innerHeight;
            const maxAllowed = Math.max(200, viewportHeight - 340);
            const contentHeight = (data.length * ROW_HEIGHT) + HEADER_HEIGHT;
            const target = Math.min(contentHeight, maxAllowed);
            setContainerHeight(`${target}px`);
        };

        updateHeight();
        window.addEventListener('resize', updateHeight);
        return () => window.removeEventListener('resize', updateHeight);
    }, [data.length]);

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

    return (
        <div style={{
            overflowX: 'auto',
            height: containerHeight,
            overflowY: 'auto',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            backgroundColor: '#fff'
        }}>
            <table style={{ ...tableStyle, marginTop: 0, boxShadow: 'none', borderRadius: 0 }}>
                <thead style={{ backgroundColor: '#f8f9fa' }}>
                    <tr>
                        {columns.map(col => (
                            <th
                                key={col.key}
                                style={thStyle}
                                onClick={() => col.sortable && requestSort(col.key)}
                            >
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    {col.label} {col.sortable && renderSortArrow(col.key)}
                                </div>
                                {enableFiltering && col.filterable && (
                                    <input
                                        type="text"
                                        style={filterInputStyle}
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
                <tbody>
                    {processedData.length === 0 ? (
                        <tr>
                            <td colSpan={columns.length} style={{ ...tdStyle, textAlign: 'center', color: '#6c757d' }}>
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
                                    <td key={`${item[idField]}-${col.key}`} style={tdStyle}>
                                        {col.render ? col.render(item) : (item[col.key] || '-')}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
}

export default GenericTable;
