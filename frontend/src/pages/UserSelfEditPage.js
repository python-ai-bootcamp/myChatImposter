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

    // Prevent Enter key from submitting the form in text inputs
    const handleInputKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
        }
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

    if (loading) return <div style={{ color: '#e2e8f0', textAlign: 'center', marginTop: '50px' }}>Loading profile...</div>;
    if (!formData) return <div style={{ color: '#e2e8f0', textAlign: 'center', marginTop: '50px' }}>Failed to load profile.</div>;

    return (
        <div className="profile-page">
            <style>{`
                .profile-page {
                    min-height: calc(100vh - 60px); /* Adjust for header if needed */
                    width: 100%;
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    color: #e2e8f0;
                    font-family: 'Inter', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: flex-start;
                    padding-top: 4rem;
                    position: relative;
                    overflow: hidden;
                }

                .profile-container {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(20px);
                    padding: 3rem;
                    border-radius: 1.5rem;
                    width: 100%;
                    max-width: 800px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    z-index: 10;
                    animation: scaleIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
                }

                .profile-header {
                    margin-bottom: 2rem;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    padding-bottom: 1rem;
                }

                .profile-header h1 {
                    font-size: 2rem;
                    font-weight: 800;
                    margin-bottom: 0.5rem;
                    background: linear-gradient(to right, #c084fc, #6366f1);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .form-group {
                    display: grid;
                    grid-template-columns: 140px 1fr;
                    align-items: center;
                    gap: 1rem;
                    margin-bottom: 1rem;
                }

                .form-group label {
                    color: #cbd5e1;
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-align: right;
                    white-space: nowrap;
                }

                .form-group input {
                    width: 100%;
                    padding: 0.75rem 1rem;
                    background: rgba(15, 23, 42, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 0.75rem;
                    color: #f8fafc;
                    font-size: 1rem;
                    transition: all 0.2s;
                    box-sizing: border-box;
                    height: 48px;
                }

                .form-group input:focus {
                    outline: none;
                    border-color: #818cf8;
                    box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2);
                    background: rgba(15, 23, 42, 0.8);
                }

                .form-group input:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                    background: rgba(15, 23, 42, 0.4);
                }

                /* Two-column row for first/last name */
                .form-row-split {
                    display: grid;
                    grid-template-columns: 140px 1fr 1fr;
                    align-items: center;
                    gap: 1rem;
                    margin-bottom: 1rem;
                }

                .form-row-split label {
                    color: #cbd5e1;
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-align: right;
                    white-space: nowrap;
                }

                .form-row-split input {
                    width: 100%;
                    padding: 0.75rem 1rem;
                    background: rgba(15, 23, 42, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 0.75rem;
                    color: #f8fafc;
                    font-size: 1rem;
                    transition: all 0.2s;
                    box-sizing: border-box;
                    height: 48px;
                }

                .form-row-split input:focus {
                    outline: none;
                    border-color: #818cf8;
                    box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2);
                    background: rgba(15, 23, 42, 0.8);
                }

                .save-button {
                    width: 100%;
                    padding: 0.75rem;
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    border: none;
                    border-radius: 0.75rem;
                    color: white;
                    font-weight: 600;
                    font-size: 1rem;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                    margin-top: 1rem;
                }

                .save-button:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);
                }

                .save-button:disabled {
                    opacity: 0.7;
                    cursor: not-allowed;
                }

                /* Background shapes */
                .shape {
                    position: absolute;
                    filter: blur(100px);
                    z-index: 0;
                    opacity: 0.4;
                    pointer-events: none;
                }
                .shape-1 {
                    top: -20%;
                    left: -20%;
                    width: 60vw;
                    height: 60vw;
                    background: radial-gradient(circle, #4f46e5 0%, transparent 70%);
                }
                .shape-2 {
                    bottom: -20%;
                    right: -20%;
                    width: 50vw;
                    height: 50vw;
                    background: radial-gradient(circle, #ec4899 0%, transparent 70%);
                }
            `}</style>

            <div className="shape shape-1" />
            <div className="shape shape-2" />

            <div className="profile-container">
                <div className="profile-header">
                    <h1>My Profile</h1>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>User ID</label>
                        <input
                            type="text"
                            value={formData.user_id}
                            disabled
                        />
                    </div>

                    <div className="form-group">
                        <label>First Name</label>
                        <input
                            type="text"
                            name="first_name"
                            value={formData.first_name || ''}
                            onChange={handleChange}
                            onKeyDown={handleInputKeyDown}
                        />
                    </div>

                    <div className="form-group">
                        <label>Last Name</label>
                        <input
                            type="text"
                            name="last_name"
                            value={formData.last_name || ''}
                            onChange={handleChange}
                            onKeyDown={handleInputKeyDown}
                        />
                    </div>

                    <div className="form-group">
                        <label>Email Address</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email || ''}
                            onChange={handleChange}
                            onKeyDown={handleInputKeyDown}
                        />
                    </div>

                    <div className="form-group">
                        <label>Phone Number</label>
                        <PhoneInputWidget
                            value={formData.phone_number}
                            onChange={(val) => setFormData(prev => ({ ...prev, phone_number: val }))}
                        />
                    </div>

                    <div className="form-group">
                        <label>Country</label>
                        <CountrySelectWidget
                            value={formData.country_value}
                            onChange={handleCountryChange}
                            darkMode={true}
                        />
                    </div>

                    <button
                        type="submit"
                        className="save-button"
                        disabled={saving}
                    >
                        {saving ? 'Saving...' : 'Save Profile'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default UserSelfEditPage;
