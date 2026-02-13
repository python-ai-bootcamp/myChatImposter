import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { logout } from '../utils/authApi';
import './GlobalHeader.css'; // We'll create this or add to index.css

const GlobalHeader = () => {
    const [user, setUser] = useState(null);
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        // If on login page, do nothing
        if (location.pathname === '/login') return;

        // Read user data from localStorage (set at login time)
        if (!user) {
            const storedRole = localStorage.getItem('role');
            const storedUserId = localStorage.getItem('user_id');
            if (storedRole && storedUserId) {
                setUser({
                    role: storedRole,
                    user_id: storedUserId,
                    first_name: localStorage.getItem('first_name'),
                    last_name: localStorage.getItem('last_name'),
                });
            }
        }
    }, [location.pathname, user]);

    const handleLogout = () => {
        logout()
            .then(() => {
                setUser(null);
                navigate('/login');
            })
            .catch(() => {
                setUser(null);
                navigate('/login');
            });
    };

    const handleLogin = () => {
        navigate('/login');
    };

    // Helper to determine if a path is active
    const isActive = (path) => {
        if (path === '/' && location.pathname === '/') return true;
        if (path !== '/' && location.pathname.startsWith(path)) return true;
        return false;
    };

    return (
        <header className="global-header">
            <div className="header-left">
                <Link to="/" className={`brand-link ${isActive('/') ? 'active' : ''}`}>
                    Home
                </Link>
                {user && (
                    <Link
                        to={user.role === 'admin' ? "/admin/dashboard" : "/operator/dashboard"}
                        className={`nav-link ${isActive(user.role === 'admin' ? "/admin/dashboard" : "/operator/dashboard") ? 'active' : ''}`}
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
                            <Link to="/admin/users" className={`nav-link ${isActive('/admin/users') ? 'active' : ''}`}>
                                Manage Users
                            </Link>
                        )}

                        <div className="user-profile">
                            <Link
                                to={user.role === 'admin' ? `/admin/users/edit/${user.user_id}` : `/operator/profile`}
                                className={`profile-link ${isActive(user.role === 'admin' ? `/admin/users/edit/${user.user_id}` : `/operator/profile`) ? 'active' : ''}`}
                            >
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
