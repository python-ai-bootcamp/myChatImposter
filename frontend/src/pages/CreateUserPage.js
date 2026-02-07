import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CountrySelectWidget from '../widgets/CountrySelectWidget';

const CreateUserPage = () => {
    const [formData, setFormData] = useState({
        user_id: '',
        first_name: '',
        last_name: '',
        email: '',
        phone_number: '',
        role: 'user',
        password: '',
        confirm_password: '',
        country_value: 'US',
        language: 'en'
    });

    const [validationErrors, setValidationErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    // Debounce helpers could go here, for now simple checks

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));

        // Clear error for field
        if (validationErrors[name]) {
            setValidationErrors(prev => ({ ...prev, [name]: null }));
        }
    };

    const handleCountryChange = (value) => {
        setFormData(prev => ({ ...prev, country_value: value }));
    };

    const validate = () => {
        const errors = {};
        if (!formData.user_id) errors.user_id = "User ID is required";
        if (!formData.first_name) errors.first_name = "First Name is required";
        if (!formData.password) errors.password = "Password is required";
        if (formData.password !== formData.confirm_password) errors.confirm_password = "Passwords do not match";
        if (formData.password.length < 8) errors.password = "Password must be at least 8 characters";

        // Regex for User ID
        if (formData.user_id && !/^[a-zA-Z0-9_-]+$/.test(formData.user_id)) {
            errors.user_id = "User ID must be alphanumeric (can include _ or -)";
        }

        setValidationErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!validate()) return;

        setLoading(true);

        try {
            const res = await fetch('/api/external/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to create user");
            }

            alert("User created successfully!");
            navigate('/admin/user/list');

        } catch (err) {
            alert(err.message);
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
            <h1>Create New User</h1>

            <form onSubmit={handleSubmit} style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>User ID *</label>
                    <input
                        type="text"
                        name="user_id"
                        value={formData.user_id}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px', borderColor: validationErrors.user_id ? 'red' : '#ccc' }}
                    />
                    {validationErrors.user_id && <span style={{ color: 'red', fontSize: '0.8rem' }}>{validationErrors.user_id}</span>}
                </div>

                <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
                    <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>First Name *</label>
                        <input
                            type="text"
                            name="first_name"
                            value={formData.first_name}
                            onChange={handleChange}
                            style={{ width: '100%', padding: '8px', borderColor: validationErrors.first_name ? 'red' : '#ccc' }}
                        />
                        {validationErrors.first_name && <span style={{ color: 'red', fontSize: '0.8rem' }}>{validationErrors.first_name}</span>}
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
                    <input
                        type="text"
                        name="phone_number"
                        value={formData.phone_number}
                        onChange={handleChange}
                        placeholder="+1234567890"
                        style={{ width: '100%', padding: '8px' }}
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
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Role *</label>
                    <select
                        name="role"
                        value={formData.role}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px' }}
                    >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>

                <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Password *</label>
                    <input
                        type="password"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px', borderColor: validationErrors.password ? 'red' : '#ccc' }}
                    />
                    {validationErrors.password && <span style={{ color: 'red', fontSize: '0.8rem' }}>{validationErrors.password}</span>}
                </div>

                <div style={{ marginBottom: '20px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Confirm Password *</label>
                    <input
                        type="password"
                        name="confirm_password"
                        value={formData.confirm_password}
                        onChange={handleChange}
                        style={{ width: '100%', padding: '8px', borderColor: validationErrors.confirm_password ? 'red' : '#ccc' }}
                    />
                    {validationErrors.confirm_password && <span style={{ color: 'red', fontSize: '0.8rem' }}>{validationErrors.confirm_password}</span>}
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    style={{
                        backgroundColor: '#28a745',
                        color: 'white',
                        padding: '10px 20px',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontSize: '1rem'
                    }}
                >
                    {loading ? 'Creating...' : 'Create User'}
                </button>
            </form>
        </div>
    );
};

export default CreateUserPage;
