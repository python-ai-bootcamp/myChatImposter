/**
 * Login Page component.
 *
 * Provides user authentication interface.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../utils/authApi';
import './LoginPage.css'; // Keeping import to not break build, but overriding styles

const LoginPage = () => {
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Validate input
      if (!userId.trim()) {
        setError('User ID is required');
        setLoading(false);
        return;
      }

      if (!password) {
        setError('Password is required');
        setLoading(false);
        return;
      }

      // Attempt login
      const response = await login(userId.trim(), password);

      if (response.success) {
        // Store user info in localStorage (persists across tabs)
        localStorage.setItem('user_id', response.user_id);
        localStorage.setItem('role', response.role);
        if (response.first_name) localStorage.setItem('first_name', response.first_name);
        if (response.last_name) localStorage.setItem('last_name', response.last_name);

        // Redirect to home page based on role
        if (response.role === 'admin') {
          navigate('/admin/dashboard');
        } else {
          navigate('/operator/dashboard');
        }
      } else {
        setError(response.message || 'Login failed');
      }
    } catch (err) {
      setError(err.message || 'An error occurred during login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <style>{`
            .login-page {
                min-height: 100vh;
                width: 100%;
                background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                color: #e2e8f0;
                font-family: 'Inter', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                position: relative;
                overflow: hidden;
            }

            .login-container {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(20px);
                padding: 3rem;
                border-radius: 1.5rem;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                z-index: 10;
                animation: scaleIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .login-header {
                text-align: center;
                margin-bottom: 2rem;
            }

            .login-header h1 {
                font-size: 2rem;
                font-weight: 800;
                margin-bottom: 0.5rem;
                background: linear-gradient(to right, #c084fc, #6366f1);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .login-header p {
                color: #94a3b8;
                font-size: 0.95rem;
            }

            .form-group {
                margin-bottom: 1.5rem;
            }

            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                color: #cbd5e1;
                font-size: 0.9rem;
                font-weight: 500;
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
            }

            .form-group input:focus {
                outline: none;
                border-color: #818cf8;
                box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2);
                background: rgba(15, 23, 42, 0.8);
            }

            /* Prevent browser autofill from turning inputs white */
            .form-group input:-webkit-autofill,
            .form-group input:-webkit-autofill:hover,
            .form-group input:-webkit-autofill:focus,
            .form-group input:-webkit-autofill:active {
                -webkit-box-shadow: 0 0 0 30px rgba(15, 23, 42, 0.95) inset !important;
                -webkit-text-fill-color: #f8fafc !important;
                caret-color: #f8fafc;
                transition: background-color 9999s ease-in-out 0s;
            }

            .form-group input {
                color-scheme: dark;
            }

            .login-button {
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
            }

            .login-button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);
            }

            .login-button:disabled {
                opacity: 0.7;
                cursor: not-allowed;
            }

            .error-message {
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.2);
                color: #fca5a5;
                padding: 0.75rem;
                border-radius: 0.75rem;
                margin-bottom: 1.5rem;
                font-size: 0.9rem;
                text-align: center;
            }

            @keyframes scaleIn {
                from { opacity: 0; transform: scale(0.95); }
                to { opacity: 1; transform: scale(1); }
            }

            /* Background shapes */
            .shape {
                position: absolute;
                filter: blur(100px);
                z-index: 0;
                opacity: 0.4;
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

      <div className="login-container">
        <div className="login-header">
          <h1>My Chat Imposter</h1>
          <p>Please sign in to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="userId">User ID</label>
            <input
              type="text"
              id="userId"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Enter your user ID"
              disabled={loading}
              autoFocus
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={loading}
              required
            />
          </div>

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
