import React from 'react';

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
    borderBottom: '2px solid #dee2e6'
};

const tdStyle = {
    padding: '12px 15px',
    borderBottom: '1px solid #dee2e6',
    verticalAlign: 'middle',
    textAlign: 'left'
};

function UserTable({ configs, selectedUserId, onSelectUser }) {
    const getTrStyle = (userId) => ({
        backgroundColor: selectedUserId === userId ? '#e9ecef' : '#fff',
        cursor: 'pointer',
        transition: 'background-color 0.2s'
    });

    return (
        <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
                <thead>
                    <tr>
                        <th style={thStyle}>User Name</th>
                        <th style={thStyle}>Authenticated</th>
                        <th style={thStyle}>Linked</th>
                    </tr>
                </thead>
                <tbody>
                    {configs.length === 0 ? (
                        <tr>
                            <td colSpan="3" style={{ ...tdStyle, textAlign: 'center', color: '#6c757d' }}>No configurations found.</td>
                        </tr>
                    ) : (
                        configs.map(config => (
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
