import React, { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

const ProtectedRoute = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(null); // null = loading
    const location = useLocation();

    useEffect(() => {
        // Validate session with backend (lightweight check)
        // Re-validates on every route change to keep proxy connections alive
        // and ensure session is still valid throughout navigation
        fetch('/api/external/auth/validate', { credentials: 'include' })
            .then(res => {
                if (res.ok) {
                    setIsAuthenticated(true);
                } else {
                    localStorage.clear();
                    setIsAuthenticated(false);
                }
            })
            .catch(() => {
                localStorage.clear();
                setIsAuthenticated(false);
            });
    }, [location.pathname]);

    if (isAuthenticated === null) {
        // Dark background to prevent white flash during initial session validation
        return <div style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)', minHeight: '100vh', width: '100vw' }} />;
    }

    if (!isAuthenticated) {
        // Redirect to login, saving the location they tried to access
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <Outlet />;
};

export default ProtectedRoute;
