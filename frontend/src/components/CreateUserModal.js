import React, { useState, useEffect, useRef, useCallback } from 'react';

const modalOverlayStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(5px)'
};

const modalContentStyle = {
    backgroundColor: '#1e1e2e',
    padding: '30px',
    borderRadius: '16px',
    maxWidth: '400px',
    width: '90%',
    boxShadow: '0 25px 50px rgba(0,0,0,0.5)',
    border: '1px solid #333'
};

const inputStyle = {
    width: '100%',
    padding: '12px 16px',
    fontSize: '1rem',
    borderRadius: '8px',
    border: '1px solid #444',
    backgroundColor: '#2a2a3e',
    color: '#fff',
    outline: 'none',
    boxSizing: 'border-box',
    marginBottom: '8px'
};

const errorStyle = {
    color: '#f87171',
    fontSize: '0.85rem',
    marginBottom: '16px',
    minHeight: '20px'
};

const successStyle = {
    color: '#4ade80',
    fontSize: '0.85rem',
    marginBottom: '16px',
    minHeight: '20px'
};

const buttonRowStyle = {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end'
};

const buttonStyle = {
    padding: '10px 20px',
    fontSize: '0.95rem',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s ease'
};

function CreateUserModal({ isOpen, onClose, onConfirm }) {
    const [botId, setBotId] = useState('');
    const [validationResult, setValidationResult] = useState(null);
    const [isValidating, setIsValidating] = useState(false);
    const debounceRef = useRef(null);

    // Debounced validation
    const validateBotId = useCallback(async (value) => {
        if (!value || value.trim() === '') {
            setValidationResult(null);
            return;
        }

        setIsValidating(true);
        try {
            const response = await fetch(`/api/external/ui/bots/validate/${encodeURIComponent(value)}`);
            if (response.ok) {
                const data = await response.json();
                setValidationResult(data);
            } else {
                setValidationResult({
                    valid: false,
                    error_code: 'network_error',
                    error_message: 'Failed to validate. Please try again.'
                });
            }
        } catch (err) {
            setValidationResult({
                valid: false,
                error_code: 'network_error',
                error_message: 'Network error. Please try again.'
            });
        } finally {
            setIsValidating(false);
        }
    }, []);

    const handleInputChange = (e) => {
        const value = e.target.value;
        setBotId(value);

        // Clear previous debounce
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        if (!value || value.trim() === '') {
            setValidationResult(null);
            return;
        }

        // Client-side regex check (Alphanumeric, -, _, 1-30 chars)
        const isValidFormat = /^[a-zA-Z0-9_-]{1,30}$/.test(value);
        if (!isValidFormat) {
            setValidationResult({
                valid: false,
                error_code: 'invalid_format',
                error_message: "Must be 1-30 chars, alphanumeric, '_' or '-'."
            });
            return; // Stop here, do not hit backend
        }

        setValidationResult(null); // Clear previous errors while waiting

        // Set new debounce (300ms) for backend check (Existence & Limit)
        debounceRef.current = setTimeout(() => {
            validateBotId(value);
        }, 300);
    };

    const handleCreate = () => {
        if (validationResult?.valid && botId.trim()) {
            onConfirm(botId.trim());
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && validationResult?.valid) {
            handleCreate();
        }
        if (e.key === 'Escape') {
            onClose();
        }
    };

    // Reset state when modal opens/closes
    useEffect(() => {
        if (!isOpen) {
            setBotId('');
            setValidationResult(null);
            setIsValidating(false);
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
            }
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const isValid = validationResult?.valid === true;
    const hasError = validationResult && !validationResult.valid;
    const canCreate = isValid && !isValidating;

    return (
        <div style={modalOverlayStyle} onClick={onClose}>
            <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
                <h2 style={{ margin: '0 0 20px 0', color: '#fff', fontSize: '1.3rem' }}>
                    Create New User
                </h2>

                <label style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '8px', display: 'block' }}>
                    Bot ID
                </label>
                <input
                    type="text"
                    value={botId}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter unique bot ID"
                    style={{
                        ...inputStyle,
                        borderColor: hasError ? '#f87171' : isValid ? '#4ade80' : '#444'
                    }}
                    autoFocus
                />

                <div style={hasError ? errorStyle : isValid ? successStyle : { minHeight: '20px', marginBottom: '16px' }}>
                    {isValidating && <span style={{ color: '#888' }}>Checking...</span>}
                    {hasError && validationResult.error_message}
                    {isValid && '✓ Bot ID is available'}
                </div>

                <div style={buttonRowStyle}>
                    <button
                        onClick={onClose}
                        style={{
                            ...buttonStyle,
                            backgroundColor: '#333',
                            color: '#fff'
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={!canCreate}
                        style={{
                            ...buttonStyle,
                            backgroundColor: canCreate ? '#6366f1' : '#444',
                            color: canCreate ? '#fff' : '#888',
                            cursor: canCreate ? 'pointer' : 'not-allowed'
                        }}
                    >
                        Create
                    </button>
                </div>
            </div>
        </div>
    );
}

export default CreateUserModal;
