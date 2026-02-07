import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import CountrySelectWidget from '../widgets/CountrySelectWidget';
import PhoneInputWidget from '../widgets/PhoneInputWidget';

const AdminUserEditPage = () => {
    const { userId } = useParams();
    const navigate = useNavigate();

    const [formData, setFormData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Password Reset State
    const [newPassword, setNewPassword] = useState('');
    const [showPasswordReset, setShowPasswordReset] = useState(false);

    const fetchUser = useCallback(() => {
        setLoading(true);
        fetch(`/api/external/users/${userId}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch user");
                return res.json();
            })
            .then(data => {
                setFormData(data);
                setLoading(false);
            })
            .catch(err => {
                alert(err.message);
                navigate('/admin/user/list');
            });
    }, [userId, navigate]);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleCountryChange = (value) => {
        setFormData(prev => ({ ...prev, country_value: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);

        try {
            const res = await fetch(`/api/external/users/${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to update user");
            }

            alert("User updated successfully!");

        } catch (err) {
            alert(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handlePasswordReset = async () => {
        if (!newPassword || newPassword.length < 8) {
            alert("Password must be at least 8 characters");
            return;
        }

        if (!window.confirm("Are you sure you want to reset this user's password? This will log them out of all sessions.")) return;

        try {
            const res = await fetch(`/api/external/users/${userId}/password`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: newPassword })
            });

            if (!res.ok) throw new Error("Failed to reset password");

            alert("Password reset successfully!");
            setNewPassword('');
            setShowPasswordReset(false);

        } catch (err) {
            alert(err.message);
        }
    };

    if (loading) return <div>Loading...</div>;
    if (!formData) return <div>User not found.</div>;

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1>Edit User: {formData.user_id}</h1>
                <button onClick={() => navigate('/admin/user/list')} style={{ backgroundColor: '#6c757d', fontSize: '0.9rem' }}>Back to List</button>
            </div>

            <form onSubmit={handleSubmit} style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '20px' }}>

                <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>First Name</label>
                        <input
                            type="text"
                            name="first_name"
                            value={formData.first_name}
                            onChange={handleChange}
                            style={{ width: '100%', padding: '8px' }}
                        />
                    </div>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Last Name</label>
                        <input
                            type="text"
                            name="last_name"
                            value={formData.last_name}
                            onChange={handleChange}
                            style={{ width: '100%', padding: '8px' }}
                        />
                    </div>
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Email Address</label>
                    <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px' }}
                    />
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Phone Number (E.164)</label>
                    <PhoneInputWidget
                        value={formData.phone_number}
                        onChange={(val) => setFormData(prev => ({ ...prev, phone_number: val }))}
                    />
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Country</label>
                    <CountrySelectWidget
                        value={formData.country_value}
                        onChange={handleCountryChange}
                    />
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Role</label>
                    <select
                        name="role"
                        value={formData.role}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px' }}
                    >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                    </select>
                    <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '5px' }}>
                        Note: Changing role will invalidate user's active sessions.
                    </p>
                </div>

                <button
                    type="submit"
                    disabled={saving}
                    style={{
                        backgroundColor: '#007bff',
                        color: 'white',
                        padding: '10px 20px',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        fontSize: '1rem'
                    }}
                >
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </form>

            {/* Password Reset Section */}
            <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', border: '1px solid #dee2e6' }}>
                <h3 style={{ marginTop: 0 }}>Security</h3>
                {!showPasswordReset ? (
                    <button
                        onClick={() => setShowPasswordReset(true)}
                        style={{ backgroundColor: '#ffc107', color: '#212529' }}
                    >
                        Reset Password
                    </button>
                ) : (
                    <div>
                        <label style={{ display: 'block', marginBottom: '5px' }}>New Password</label>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            style={{ padding: '8px', marginRight: '10px' }}
                        />
                        <button
                            onClick={handlePasswordReset}
                            style={{ backgroundColor: '#dc3545', color: 'white', marginRight: '10px' }}
                        >
                            Confirm Reset
                        </button>
                        <button
                            onClick={() => { setShowPasswordReset(false); setNewPassword(''); }}
                            style={{ backgroundColor: '#6c757d', color: 'white' }}
                        >
                            Cancel
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AdminUserEditPage;
