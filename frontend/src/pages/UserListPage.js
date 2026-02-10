import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import GenericTable from '../components/GenericTable';

const UserListPage = ({ enableFiltering = true }) => {
    const [users, setUsers] = useState([]);
    const [selectedUserId, setSelectedUserId] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isCompact, setIsCompact] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        const handleResize = () => {
            setIsCompact(window.innerHeight < 900);
        };
        handleResize();
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = () => {
        setLoading(true);
        fetch('/api/external/users')
            .then(res => {
                if (!res.ok) {
                    if (res.status === 403) throw new Error("Access Denied");
                    throw new Error("Failed to fetch users");
                }
                return res.json();
            })
            .then(data => {
                setUsers(data);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    };

    const handleDelete = async () => {
        if (!selectedUserId) return;

        if (!window.confirm(`Are you sure you want to delete user ${selectedUserId}? This action cannot be undone.`)) {
            return;
        }

        try {
            const res = await fetch(`/api/external/users/${selectedUserId}`, { method: 'DELETE' });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to delete");
            }
            // Success
            setUsers(users.filter(u => u.user_id !== selectedUserId));
            setSelectedUserId(null); // Deselect
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    const handleEdit = () => {
        if (selectedUserId) {
            navigate(`/admin/users/edit/${selectedUserId}`);
        }
    };

    const handleAdd = () => {
        navigate('/admin/users/create');
    };

    const handleResetPassword = () => {
        if (selectedUserId) {
            const newPassword = prompt("Enter new password for " + selectedUserId + ":");
            if (newPassword) {
                fetch(`/api/external/users/${selectedUserId}/password`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: newPassword })
                })
                    .then(res => {
                        if (!res.ok) return res.json().then(d => { throw new Error(d.detail || "Failed") });
                        alert("Password reset successfully.");
                    })
                    .catch(err => alert("Error: " + err.message));
            }
        }
    };

    const columns = [
        { key: 'user_id', label: 'User ID', sortable: true, filterable: true, width: '15%' },
        {
            key: 'name',
            label: 'Name',
            sortable: true,
            filterable: true,
            width: '25%',
            getValue: (user) => `${user.first_name} ${user.last_name}`,
            render: (user) => `${user.first_name} ${user.last_name}`
        },
        {
            key: 'role',
            label: 'Role',
            sortable: true,
            filterable: true,
            width: '15%',
            render: (user) => (
                <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: user.role === 'admin' ? '#0ea5e9' : '#64748b', // Updated colors for dark mode
                    color: 'white',
                    fontSize: '0.8rem',
                    fontWeight: 600
                }}>
                    {user.role}
                </span>
            )
        },
        { key: 'email', label: 'Email', sortable: true, filterable: true, width: '25%' },
        { key: 'country_value', label: 'Country', sortable: true, filterable: true, width: '20%' },
    ];

    // Styles matching HomePage
    const pageStyle = {
        height: 'calc(100vh - 60px)',
        width: '100vw',
        fontFamily: "'Inter', 'system-ui', sans-serif",
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: isCompact ? '1rem' : '3rem 2rem',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)',
        position: 'relative',
        overflow: 'hidden',
        boxSizing: 'border-box',
        flexDirection: 'column',
    };

    const glassBase = {
        background: 'rgba(30, 41, 59, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(20px)',
        width: '100%',
        maxWidth: '1200px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        boxSizing: 'border-box',
    };

    const headerPanelStyle = {
        ...glassBase,
        padding: '1.5rem',
        borderRadius: '1.5rem',
        borderBottomLeftRadius: '0.3rem',
        borderBottomRightRadius: '0.3rem',
        marginBottom: '10px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        zIndex: 20,
    };

    const rowHeight = isCompact ? 40 : 60;
    const overhead = isCompact ? 160 : 250;
    const minTableHeight = isCompact ? 350 : 450;
    const estimatedHeight = Math.max(minTableHeight, (users.length * rowHeight) + overhead);

    const bodyPanelStyle = {
        ...glassBase,
        padding: isCompact ? '0.5rem' : '1rem',
        borderRadius: '1.5rem',
        borderTopLeftRadius: '0.3rem',
        borderTopRightRadius: '0.3rem',
        height: `min(calc(100vh - 16rem), ${estimatedHeight}px)`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 10,
    };

    const headerStyle = {
        fontSize: '2.5rem',
        fontWeight: 800,
        margin: 0,
        background: 'linear-gradient(to right, #38bdf8, #818cf8)', // Slightly different gradient for Users
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        textShadow: '0 10px 20px rgba(0,0,0,0.2)',
    };

    const actionButtonsContainerStyle = {
        display: 'flex',
        gap: '1rem',
        marginTop: '1rem',
        paddingTop: '1rem',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        marginBottom: '20px'
    };

    const getButtonStyle = (type, disabled) => {
        const base = {
            padding: '10px 20px',
            fontSize: '0.9rem',
            fontWeight: 600,
            border: 'none',
            borderRadius: '0.75rem',
            cursor: disabled ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.5 : 1,
            transition: 'all 0.2s ease',
            boxShadow: disabled ? 'none' : '0 4px 12px rgba(0, 0, 0, 0.3)',
            color: 'white',
        };

        if (disabled) return { ...base, background: '#475569', color: '#94a3b8', boxShadow: 'none' };

        switch (type) {
            case 'success': // Create User
                return { ...base, background: 'linear-gradient(135deg, #10b981, #059669)' };
            case 'primary': // Edit
                return { ...base, background: 'linear-gradient(135deg, #3b82f6, #2563eb)' };
            case 'warning': // Reset Password
                return { ...base, background: 'linear-gradient(135deg, #f59e0b, #d97706)' };
            case 'danger': // Delete
                return { ...base, background: 'linear-gradient(135deg, #ef4444, #dc2626)' };
            default:
                return base;
        }
    };

    if (loading) return (
        <div style={{ ...pageStyle, justifyContent: 'center' }}>
            <div style={{ color: 'white', fontSize: '1.5rem' }}>Loading users...</div>
        </div>
    );

    return (
        <div style={pageStyle}>
            {/* Header Panel */}
            <div style={headerPanelStyle}>
                <h2 style={headerStyle}>User Management</h2>
            </div>

            {/* Body Panel */}
            <div style={bodyPanelStyle}>
                {error && <div style={{ color: '#fca5a5', marginBottom: '1rem', padding: '12px', backgroundColor: 'rgba(239, 68, 68, 0.2)', borderRadius: '0.5rem', border: '1px solid rgba(239, 68, 68, 0.3)' }}>Error: {error}</div>}

                <GenericTable
                    data={users}
                    columns={columns}
                    idField="user_id"
                    selectedId={selectedUserId}
                    onSelect={setSelectedUserId}
                    enableFiltering={enableFiltering}
                    darkMode={true}
                    compact={isCompact}
                    style={{
                        minHeight: isCompact ? '200px' : '300px',
                        marginTop: 0
                    }}
                />

                <div style={actionButtonsContainerStyle}>
                    <button
                        onClick={handleAdd}
                        style={getButtonStyle('success', false)}
                    >
                        Create User
                    </button>

                    <button
                        onClick={handleEdit}
                        disabled={!selectedUserId}
                        style={getButtonStyle('primary', !selectedUserId)}
                    >
                        Edit
                    </button>

                    <button
                        onClick={handleResetPassword}
                        disabled={!selectedUserId}
                        style={getButtonStyle('warning', !selectedUserId)}
                    >
                        Reset Password
                    </button>

                    <button
                        onClick={handleDelete}
                        disabled={!selectedUserId}
                        style={getButtonStyle('danger', !selectedUserId)}
                    >
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
};

export default UserListPage;
