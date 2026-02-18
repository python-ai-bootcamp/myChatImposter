import React, { useState, useEffect, useCallback } from 'react';
import CountrySelectWidget from '../components/widgets/CountrySelectWidget';
import PhoneInputWidget from '../components/widgets/PhoneInputWidget';
import { LanguageSelectWidget } from '../components/widgets/LanguageSelectWidget';

const UserSelfEditPage = () => {
    const [formData, setFormData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [userId, setUserId] = useState(null);
    const [validationErrors, setValidationErrors] = useState({});

    useEffect(() => {
        const storedUserId = localStorage.getItem('user_id');
        if (!storedUserId) {
            setLoading(false);
            return;
        }
        setUserId(storedUserId);
        fetch(`/api/external/users/${storedUserId}`)
            .then(res => res.json())
            .then(data => {
                // Ensure defaults
                if (!data.language) data.language = 'en';
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

        if (validationErrors[name]) {
            setValidationErrors(prev => ({ ...prev, [name]: null }));
        }
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

    const handleLanguageChange = (value) => {
        setFormData(prev => ({ ...prev, language: value }));
        if (validationErrors.language) {
            setValidationErrors(prev => ({ ...prev, language: null }));
        }
    };

    const validate = useCallback(() => {
        if (!formData) return false;
        const errors = {};
        const phoneRegex = /^\+\d{10,15}$/;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!formData.first_name || formData.first_name.trim() === '') errors.first_name = "First Name is required";
        if (!formData.last_name || formData.last_name.trim() === '') errors.last_name = "Last Name is required";

        if (!formData.email || !emailRegex.test(formData.email)) {
            errors.email = "A valid email address is required";
        }

        if (formData.phone_number && !phoneRegex.test(formData.phone_number)) {
            errors.phone_number = "Invalid phone number format. Please use E.164 (e.g., +1234567890).";
        }
        if (!formData.phone_number) {
            errors.phone_number = "Phone number is required";
        }

        if (!formData.gov_id || formData.gov_id.trim() === '') {
            errors.gov_id = "Government ID is required";
        }
        if (!formData.country_value) {
            errors.country_value = "Country is required";
        }

        if (!formData.language) {
            errors.language = "Language is required";
        }

        setValidationErrors(errors);
        return Object.keys(errors).length === 0;
    }, [formData]);

    // Debounced validation
    useEffect(() => {
        const timer = setTimeout(() => {
            if (formData) {
                validate();
            }
        }, 500);

        return () => clearTimeout(timer);
    }, [formData, validate]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validate()) return;

        setSaving(true);

        try {
            const res = await fetch(`/api/external/users/${userId}`, {
                method: 'PATCH', // or PATCH if supported
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

    const pageBackground = { background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)', minHeight: 'calc(100vh - 60px)', width: '100vw' };

    if (loading) return <div style={pageBackground} />;
    if (!formData) return <div style={{ ...pageBackground, color: '#e2e8f0', textAlign: 'center', paddingTop: '50px' }}>Failed to load profile.</div>;

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
                    align-items: center; /* Center vertically */
                    padding-top: 2rem;
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
                    max-height: 90vh; /* changed from animation to proper bounds */
                    overflow-y: auto;
                    scrollbar-width: none;
                }
/* ... existing styles ... */
                        <div style={{ width: '100%' }}>
                            <CountrySelectWidget
                                value={formData.country_value}
                                onChange={handleCountryChange}
                                darkMode={true}
                                error={validationErrors.country_value}
                            />
                        </div>
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

                /* Autofill styling fix */
                input:-webkit-autofill,
                input:-webkit-autofill:hover, 
                input:-webkit-autofill:active {
                    -webkit-box-shadow: 0 0 0 1000px #0f172a inset !important;
                    -webkit-text-fill-color: #f8fafc !important;
                    caret-color: #f8fafc;
                    border: 1px solid rgba(255, 255, 255, 0.1) !important;
                    transition: background-color 5000s ease-in-out 0s;
                }

                input:-webkit-autofill:focus {
                    -webkit-box-shadow: 0 0 0 1000px #0f172a inset, 0 0 0 3px rgba(129, 140, 248, 0.2) !important;
                    -webkit-text-fill-color: #f8fafc !important;
                    caret-color: #f8fafc;
                    border-color: #818cf8 !important;
                    transition: background-color 5000s ease-in-out 0s;
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
                            style={{ border: validationErrors.first_name ? '1px solid #ef4444' : undefined }}
                            title={validationErrors.first_name || ''}
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
                            style={{ border: validationErrors.last_name ? '1px solid #ef4444' : undefined }}
                            title={validationErrors.last_name || ''}
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
                            style={{ border: validationErrors.email ? '1px solid #ef4444' : undefined }}
                            title={validationErrors.email || ''}
                        />
                    </div>

                    <div className="form-group">
                        <label>Government ID *</label>
                        <div style={{ width: '100%' }}>
                            <input
                                type="text"
                                name="gov_id"
                                value={formData.gov_id || ''}
                                onChange={handleChange}
                                onKeyDown={handleInputKeyDown}
                                placeholder="e.g. Passport or National ID"
                                style={{
                                    borderColor: validationErrors.gov_id ? '#ef4444' : 'rgba(255, 255, 255, 0.1)'
                                }}
                                title={validationErrors.gov_id || ''}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Phone Number</label>
                        <div style={{ width: '100%' }}>
                            <PhoneInputWidget
                                value={formData.phone_number}
                                onChange={(val) => setFormData(prev => ({ ...prev, phone_number: val }))}
                                error={validationErrors.phone_number}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Country</label>
                        <div style={{ width: '100%' }}>
                            <CountrySelectWidget
                                value={formData.country_value}
                                onChange={handleCountryChange}
                                darkMode={true}
                                error={validationErrors.country_value}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Language *</label>
                        <div style={{ width: '100%' }}>
                            <LanguageSelectWidget
                                value={formData.language}
                                onChange={handleLanguageChange}
                                darkMode={true}
                                error={validationErrors.language}
                            />
                        </div>
                    </div>

                    {/* Quota Section (Read Only) */}
                    <div style={{ marginTop: '2rem', marginBottom: '2rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1rem' }}>
                        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', color: '#cbd5e1' }}>My LLM Quota</h3>

                        {formData.llm_quota && formData.llm_quota.enabled === false ? (
                            <div style={{ color: '#ef4444', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem' }}>
                                Quota is currently disabled. Your bots may not respond.
                            </div>
                        ) : (
                            <div style={{ display: 'grid', gap: '1rem', background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Usage</span>
                                    <span style={{ color: '#e2e8f0', fontWeight: 600 }}>
                                        ${formData.llm_quota?.dollars_used?.toFixed(4) || '0.0000'} / ${formData.llm_quota?.dollars_per_period?.toFixed(2) || '1.00'}
                                    </span>
                                </div>

                                {/* Progress Bar */}
                                <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div style={{
                                        height: '100%',
                                        width: `${Math.min(((formData.llm_quota?.dollars_used || 0) / (formData.llm_quota?.dollars_per_period || 1)) * 100, 100)}%`,
                                        background: (formData.llm_quota?.dollars_used || 0) >= (formData.llm_quota?.dollars_per_period || 1) ? '#ef4444' : '#10b981'
                                    }} />
                                </div>

                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#94a3b8' }}>
                                    <span>Resets every {formData.llm_quota?.reset_days || 7} days</span>
                                    <span>Last Reset: {formData.llm_quota?.last_reset ? new Date(formData.llm_quota.last_reset).toLocaleDateString() : 'Never'}</span>
                                </div>
                            </div>
                        )}
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
