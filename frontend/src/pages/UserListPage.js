import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import GenericTable from '../components/GenericTable';

// Styles matching HomePage
const pageStyle = {
    maxWidth: '1200px',
    margin: '40px auto',
    padding: '2rem',
    backgroundColor: '#fff',
    fontFamily: "'Inter', sans-serif",
};

const actionButtonsContainerStyle = {
    display: 'flex',
    gap: '1rem',
    marginTop: '2rem',
    paddingTop: '1rem',
    borderTop: '1px solid #dee2e6',
    marginBottom: '20px'
};

const getButtonStyle = (type, disabled) => {
    const base = {
        padding: '8px 16px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        borderRadius: '4px',
        fontSize: '0.9rem',
        transition: 'all 0.2s',
        opacity: disabled ? 0.6 : 1,
        backgroundColor: disabled ? '#e9ecef' : '#f8f9fa',
        color: disabled ? '#6c757d' : '#212529',
        border: disabled ? '1px solid #ced4da' : '1px solid #ccc'
    };

    if (disabled) return base;

    switch (type) {
        case 'primary':
            return { ...base, backgroundColor: '#007bff', color: 'white', border: 'none' };
        case 'danger':
            return { ...base, backgroundColor: '#dc3545', color: 'white', border: 'none' };
        case 'success':
            return { ...base, backgroundColor: '#28a745', color: 'white', border: 'none' };
        case 'warning':
            return { ...base, backgroundColor: '#ffc107', color: '#212529', border: 'none' };
        default:
            return base;
    }
};

const UserListPage = ({ enableFiltering = true }) => {
    const [users, setUsers] = useState([]);
    const [selectedUserId, setSelectedUserId] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

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
                    backgroundColor: user.role === 'admin' ? '#007bff' : '#6c757d',
                    color: 'white',
                    fontSize: '0.8rem'
                }}>
                    {user.role}
                </span>
            )
        },
        { key: 'email', label: 'Email', sortable: true, filterable: true, width: '25%' },
        { key: 'country_value', label: 'Country', sortable: true, filterable: true, width: '20%' },
    ];

    if (loading) return <div style={pageStyle}>Loading users...</div>;

    return (
        <div style={pageStyle}>
            <h2 style={{ margin: 0, marginBottom: '1rem' }}>User Management</h2>

            {error && <div style={{ color: 'red', marginTop: '1rem', padding: '10px', backgroundColor: '#fff5f5', borderRadius: '4px' }}>Error: {error}</div>}

            <GenericTable
                data={users}
                columns={columns}
                idField="user_id"
                selectedId={selectedUserId}
                onSelect={setSelectedUserId}
                enableFiltering={enableFiltering}
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
    );
};

export default UserListPage;
