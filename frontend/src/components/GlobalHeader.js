import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import './GlobalHeader.css'; // We'll create this or add to index.css

const GlobalHeader = () => {
    const [user, setUser] = useState(null);
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        // If on login page, do nothing (header is hidden anyway by the check below, but good practice)
        if (location.pathname === '/login') return;

        // If user is already loaded, we might not need to refetch, 
        // but if we just logged in, user is null.
        if (!user) {
            fetch('/api/external/auth/me', { credentials: 'include' })
                .then(res => {
                    if (res.ok) return res.json();
                    throw new Error('Not authenticated');
                })
                .then(data => setUser(data))
                .catch(() => {
                    // Silent fail or redirect
                });
        }
    }, [location.pathname, user]);

    const handleLogout = () => {
        fetch('/api/external/auth/logout', { method: 'POST' })
            .then(() => {
                setUser(null);
                navigate('/login');
            });
    };

    const handleLogin = () => {
        navigate('/login');
    };

    return (
        <header className="global-header">
            <div className="header-left">
                <Link to="/" className="brand-link">
                    Home
                </Link>
                {user && (
                    <Link
                        to={user.role === 'admin' ? "/admin/dashboard" : "/operator/dashboard"}
                        className="nav-link"
                        style={{ marginLeft: '20px' }}
                    >
                        Manage Bot Farm
                    </Link>
                )}
            </div>
            <div className="header-right">
                {user ? (
                    <>
                        {user.role === 'admin' && (
                            <Link to="/admin/users" className="nav-link">
                                Manage Users
                            </Link>
                        )}

                        <div className="user-profile">
                            <Link to={user.role === 'admin' ? `/admin/users/edit/${user.user_id}` : `/operator/profile`} className="profile-link">
                                <div className="avatar">
                                    {user.first_name ? user.first_name.charAt(0).toUpperCase() : 'U'}
                                </div>
                                <span className="user-name">
                                    {user.first_name} {user.last_name}
                                </span>
                            </Link>
                        </div>

                        <button onClick={handleLogout} className="logout-btn-header">
                            Logout
                        </button>
                    </>
                ) : (
                    location.pathname !== '/login' && (
                        <button onClick={handleLogin} className="logout-btn-header">
                            Login
                        </button>
                    )
                )}
            </div>
        </header>
    );
};

export default GlobalHeader;
