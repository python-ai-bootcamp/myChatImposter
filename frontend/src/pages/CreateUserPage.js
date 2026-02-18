import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import CountrySelectWidget from '../components/widgets/CountrySelectWidget';
import PhoneInputWidget from '../components/widgets/PhoneInputWidget';
import { LanguageSelectWidget } from '../components/widgets/LanguageSelectWidget';

const CreateUserPage = () => {
    const navigate = useNavigate();
    const location = useLocation();

    // Get user_id from navigation state (passed from UserListPage modal)
    const predefinedUserId = location.state?.user_id;

    const [formData, setFormData] = useState({
        user_id: predefinedUserId || '',
        first_name: '',
        last_name: '',
        email: '',
        phone_number: '',
        role: 'user',
        password: '',
        confirm_password: '',
        gov_id: '',
        country_value: 'US', // Default to US as per image
        language: 'en',
        llm_quota: {
            enabled: true,
            reset_days: 7,
            dollars_per_period: 1.0
        }
    });

    const [validationErrors, setValidationErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    useEffect(() => {
        // Redirect if no user_id passed
        if (!predefinedUserId) {
            alert("Please start from the User List page to create a user.");
            navigate('/admin/users');
        } else {
            setFormData(prev => ({ ...prev, user_id: predefinedUserId }));
        }
    }, [predefinedUserId, navigate]);

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

    const handleQuotaChange = (e) => {
        const { name, value, type, checked } = e.target;
        const val = type === 'checkbox' ? checked : value;

        setFormData(prev => ({
            ...prev,
            llm_quota: {
                ...prev.llm_quota,
                [name]: type === 'number' ? parseFloat(val) : val
            }
        }));
    };

    const validate = useCallback(() => {
        const errors = {};
        // Initial empty state should show errors if we want "validation once after loading"
        // But usually we don't want to show errors on a fresh empty form immediately.
        // However, user requested: "UI validations are cheap, make them happen once after loading of the page"
        // So checking emptiness immediately is correct per request.

        if (!formData.first_name) errors.first_name = "First Name is required";
        if (!formData.last_name) errors.last_name = "Last Name is required";
        if (!formData.password) errors.password = "Password is required";
        if (formData.password !== formData.confirm_password) errors.confirm_password = "Passwords do not match";
        if (!formData.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) errors.email = "A valid email address is required";
        if (!formData.phone_number) errors.phone_number = "Phone Number is required";

        if (formData.password.length < 8) {
            errors.password = "Password must be at least 8 characters long";
        } else if (!/[A-Z]/.test(formData.password)) {
            errors.password = "Password must contain at least one uppercase letter";
        } else if (!/[a-z]/.test(formData.password)) {
            errors.password = "Password must contain at least one lowercase letter";
        } else if (!/\d/.test(formData.password)) {
            errors.password = "Password must contain at least one digit";
        } else if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(formData.password)) {
            errors.password = "Password must contain at least one special character/symbol";
        }
        if (!formData.gov_id || formData.gov_id.trim() === '') errors.gov_id = "Government ID is required";
        if (!formData.country_value) errors.country_value = "Country is required";
        if (!formData.language) errors.language = "Language is required";

        setValidationErrors(errors);
        return Object.keys(errors).length === 0;
    }, [formData]);

    // Debounced validation
    useEffect(() => {
        const timer = setTimeout(() => {
            validate();
        }, 500);

        return () => clearTimeout(timer);
    }, [formData, validate]);

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
            navigate('/admin/users');

        } catch (err) {
            alert(err.message);
            setLoading(false);
        }
    };

    if (!predefinedUserId) return null;

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
                    overflow: hidden;
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
                    border: 0px solid rgba(255, 255, 255, 0.1);
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
                
                .form-group input[disabled] {
                     background: rgba(15, 23, 42, 0.4);
                     cursor: not-allowed;
                     opacity: 0.7;
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
                    border: 0px solid rgba(255, 255, 255, 0.1);
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
                    <h1>Finalize User Account</h1>
                    <button onClick={() => navigate('/admin/users')} className="back-button">
                        Cancel
                    </button>
                </div>

                <div className="form-content">
                    <form onSubmit={handleSubmit} autoComplete="off">
                        {/* Hidden inputs to trick browser autofill */}
                        <input type="text" style={{ display: 'none' }} />
                        <input type="password" style={{ display: 'none' }} />

                        {/* User ID (Read-Only) */}
                        <div className="form-group">
                            <label>User ID</label>
                            <input
                                type="text"
                                value={formData.user_id}
                                disabled
                                autoComplete="off"
                            />
                        </div>

                        {/* Name Split */}
                        <div className="form-row-split">
                            <label>Name</label>
                            <div style={{ width: '100%' }}>
                                <input
                                    type="text"
                                    name="first_name"
                                    placeholder="First Name *"
                                    value={formData.first_name}
                                    onChange={handleChange}
                                    autoComplete="new-password" // Trick to prevent name autofill
                                    style={{ border: validationErrors.first_name ? '1px solid #ef4444' : undefined }}
                                    title={validationErrors.first_name || ''}
                                />
                            </div>
                            <input
                                type="text"
                                name="last_name"
                                placeholder="Last Name *"
                                value={formData.last_name}
                                onChange={handleChange}
                                autoComplete="new-password"
                                style={{ border: validationErrors.last_name ? '1px solid #ef4444' : undefined }}
                                title={validationErrors.last_name || ''}
                            />
                        </div>

                        {/* Email */}
                        <div className="form-group">
                            <label>Email Address</label>
                            <input
                                type="email"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                autoComplete="new-password" // Often works better than 'off' for emails
                                style={{ border: validationErrors.email ? '1px solid #ef4444' : undefined }}
                                title={validationErrors.email || ''}
                            />
                        </div>

                        {/* Gov ID */}
                        <div className="form-group">
                            <label>Government ID *</label>
                            <div style={{ width: '100%' }}>
                                <input
                                    type="text"
                                    name="gov_id"
                                    value={formData.gov_id}
                                    onChange={handleChange}
                                    placeholder="e.g. Passport or National ID"
                                    autoComplete="off"
                                    style={{ border: validationErrors.gov_id ? '1px solid #ef4444' : undefined }}
                                    title={validationErrors.gov_id || ''}
                                />
                            </div>
                        </div>

                        {/* Phone */}
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

                        {/* Country */}
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

                        {/* Language */}
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

                        {/* Role */}
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

                        {/* Quota Section */}
                        <div style={{ marginTop: '1rem', marginBottom: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1rem' }}>
                            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', color: '#cbd5e1' }}>LLM Quota</h3>

                            <div className="form-group">
                                <label>Enabled</label>
                                <div style={{ display: 'flex', alignItems: 'center', height: '48px' }}>
                                    <input
                                        type="checkbox"
                                        name="enabled"
                                        checked={formData.llm_quota.enabled}
                                        onChange={handleQuotaChange}
                                        style={{ width: '20px', height: '20px', margin: 0 }}
                                    />
                                </div>
                            </div>

                            <div className="form-row-split">
                                <label>Limits</label>
                                <div className="form-group" style={{ gridTemplateColumns: '1fr', gap: '0.5rem', margin: 0 }}>
                                    <span style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>Reset Days</span>
                                    <input
                                        type="number"
                                        name="reset_days"
                                        value={formData.llm_quota.reset_days}
                                        onChange={handleQuotaChange}
                                        min="1"
                                    />
                                </div>
                                <div className="form-group" style={{ gridTemplateColumns: '1fr', gap: '0.5rem', margin: 0 }}>
                                    <span style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>$ Limit / Period</span>
                                    <input
                                        type="number"
                                        name="dollars_per_period"
                                        value={formData.llm_quota.dollars_per_period}
                                        onChange={handleQuotaChange}
                                        step="0.01"
                                        min="0"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Password */}
                        <div className="form-group">
                            <label>Password *</label>
                            <div style={{ width: '100%', position: 'relative' }} title={validationErrors.password || ''}>
                                <input
                                    type={showPassword ? "text" : "password"}
                                    name="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    autoComplete="new-password"
                                    style={{ border: validationErrors.password ? '1px solid #ef4444' : undefined, paddingRight: '40px' }}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    style={{
                                        position: 'absolute',
                                        right: '10px',
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        background: 'transparent',
                                        border: 'none',
                                        color: '#cbd5e1',
                                        cursor: 'pointer',
                                        padding: 0,
                                        display: 'flex',
                                        alignItems: 'center'
                                    }}
                                >
                                    {showPassword ? (
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                                    ) : (
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Confirm Password */}
                        <div className="form-group">
                            <label>Confirm Password *</label>
                            <div style={{ width: '100%', position: 'relative' }} title={validationErrors.confirm_password || ''}>
                                <input
                                    type={showPassword ? "text" : "password"}
                                    name="confirm_password"
                                    value={formData.confirm_password}
                                    onChange={handleChange}
                                    autoComplete="new-password"
                                    style={{ border: validationErrors.confirm_password ? '1px solid #ef4444' : undefined, paddingRight: '40px' }}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    style={{
                                        position: 'absolute',
                                        right: '10px',
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        background: 'transparent',
                                        border: 'none',
                                        color: '#cbd5e1',
                                        cursor: 'pointer',
                                        padding: 0,
                                        display: 'flex',
                                        alignItems: 'center'
                                    }}
                                >
                                    {showPassword ? (
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                                    ) : (
                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="save-button"
                            disabled={loading}
                        >
                            {loading ? 'Creating Account (Securely)...' : 'Create Account'}
                        </button>
                    </form>
                </div>
            </div >
        </div >
    );
};

export default CreateUserPage;
