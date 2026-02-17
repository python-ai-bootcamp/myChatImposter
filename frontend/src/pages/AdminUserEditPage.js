import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import CountrySelectWidget from '../components/widgets/CountrySelectWidget';
import PhoneInputWidget from '../components/widgets/PhoneInputWidget';
import { LanguageSelectWidget } from '../components/widgets/LanguageSelectWidget';

const AdminUserEditPage = () => {
    const { userId } = useParams();
    const navigate = useNavigate();

    const [formData, setFormData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [validationErrors, setValidationErrors] = useState({});

    const fetchUser = useCallback(() => {
        setLoading(true);
        fetch(`/api/external/users/${userId}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch user");
                return res.json();
            })
            .then(data => {
                // Ensure defaults
                if (!data.language) data.language = 'en';
                setFormData(data);
                setLoading(false);
            })
            .catch(err => {
                alert(err.message);
                navigate('/admin/users');
            });
    }, [userId, navigate]);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));

        if (validationErrors[name]) {
            setValidationErrors(prev => ({ ...prev, [name]: null }));
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

    const pageBackground = { background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)', minHeight: 'calc(100vh - 60px)', width: '100vw' };

    if (loading) return <div style={pageBackground} />;
    if (!formData) return <div style={{ ...pageBackground, color: '#e2e8f0', textAlign: 'center', paddingTop: '50px' }}>User not found.</div>;

    return (
        <div className="profile-page">
            <style>{`
                .profile-page {
                    height: calc(100vh - 60px);
                    width: 100%;
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    color: #e2e8f0;
                    font-family: 'Inter', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 2rem;
                    position: relative;
                    overflow: hidden; /* Prevent external scroll */
                    box-sizing: border-box;
                }

                .profile-container {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(20px);
                    padding: 2rem;
                    border-radius: 1.5rem;
                    width: 100%;
                    max-width: 800px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    z-index: 10;
                    display: flex;
                    flex-direction: column;
                    /* height: 100%; Removed to allow auto-height */
                    max-height: 100%;
                    overflow: hidden;
                }

                .profile-header {
                    margin-bottom: 1.5rem;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    padding-bottom: 1rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-shrink: 0;
                }

                .form-content {
                    flex: 1;
                    overflow-y: auto;
                    min-height: 0;
                    padding-right: 10px;
                    scrollbar-width: thin;
                    scrollbar-color: rgba(255,255,255,0.2) transparent;
                }
                .form-content::-webkit-scrollbar {
                    width: 6px;
                }
                .form-content::-webkit-scrollbar-thumb {
                    background-color: rgba(255,255,255,0.2);
                    border-radius: 3px;
                }

                .profile-header h1 {
                    font-size: 2rem;
                    font-weight: 800;
                    margin: 0;
                    background: linear-gradient(to right, #c084fc, #6366f1);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .back-button {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    color: #e2e8f0;
                    padding: 8px 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 0.9rem;
                    transition: all 0.2s;
                }

                .back-button:hover {
                    background: rgba(255, 255, 255, 0.2);
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

                .form-group input, .form-group select {
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

                .form-group input:focus, .form-group select:focus {
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
                    background: linear-gradient(135deg, #3b82f6, #2563eb);
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
                    box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
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
                    <h1>Edit User</h1>
                    <button onClick={() => navigate('/admin/users')} className="back-button">
                        Back to List
                    </button>
                </div>

                <div className="form-content">

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label>User ID</label>
                            <input
                                type="text"
                                value={formData.user_id}
                                disabled
                            />
                        </div>

                        <div className="form-row-split">
                            <label>Name</label>
                            <input
                                type="text"
                                name="first_name"
                                placeholder="First Name"
                                value={formData.first_name || ''}
                                onChange={handleChange}
                                style={{ border: validationErrors.first_name ? '1px solid #ef4444' : undefined }}
                                title={validationErrors.first_name || ''}
                            />
                            <input
                                type="text"
                                name="last_name"
                                placeholder="Last Name"
                                value={formData.last_name || ''}
                                onChange={handleChange}
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

                        <div className="form-group">
                            <label>Role</label>
                            <select
                                name="role"
                                value={formData.role}
                                onChange={handleChange}
                            >
                                <option value="user">User</option>
                                <option value="admin">Admin</option>
                            </select>
                        </div>

                        <button
                            type="submit"
                            className="save-button"
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>
                    </form>
                </div>

            </div>
        </div >
    );
};

export default AdminUserEditPage;
