import React, { useState, useEffect } from 'react';
import CountrySelectWidget from '../widgets/CountrySelectWidget';
import PhoneInputWidget from '../widgets/PhoneInputWidget';

const UserSelfEditPage = () => {
    const [formData, setFormData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [userId, setUserId] = useState(null);

    useEffect(() => {
        // 1. Get current user ID from /me
        fetch('/api/external/auth/me')
            .then(res => {
                if (res.ok) return res.json();
                throw new Error("Not authenticated");
            })
            .then(data => {
                setUserId(data.user_id);
                // 2. Fetch details for this user (using self-access)
                return fetch(`/api/external/users/${data.user_id}`);
            })
            .then(res => res.json())
            .then(data => {
                setFormData(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        if (name === 'user_id' || name === 'role') return; // Prevent editing these
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleCountryChange = (value) => {
        setFormData(prev => ({ ...prev, country_value: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validation
        const phoneRegex = /^\+?[1-9]\d{1,14}$/;
        if (formData.phone_number && !phoneRegex.test(formData.phone_number)) {
            alert("Invalid phone number format. Please use E.164 format (e.g., +1234567890).");
            return;
        }

        setSaving(true);

        try {
            const res = await fetch(`/api/external/users/${userId}`, {
                method: 'PUT', // or PATCH if supported
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to update profile");
            }

            alert("Profile updated successfully!");

        } catch (err) {
            alert(err.message);
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div>Loading profile...</div>;
    if (!formData) return <div>Failed to load profile.</div>;

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
            <h1>My Profile</h1>

            <form onSubmit={handleSubmit} style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>

                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>User ID</label>
                    <input
                        type="text"
                        value={formData.user_id}
                        disabled
                        style={{ width: '100%', padding: '8px', backgroundColor: '#e9ecef', cursor: 'not-allowed' }}
                    />
                </div>

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
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Phone Number</label>
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
                    {saving ? 'Saving...' : 'Save Profile'}
                </button>
            </form>
        </div>
    );
};

export default UserSelfEditPage;
