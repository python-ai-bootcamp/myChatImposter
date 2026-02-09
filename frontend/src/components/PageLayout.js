import React from 'react';

// Light theme styles
const lightStyles = {
    pageContainer: {
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 180px)',
        width: '100%',
        boxSizing: 'border-box',
        padding: '20px 20px 0 20px',
    },
    whiteCard: {
        maxWidth: '1800px',
        width: '100%',
        margin: '0 auto',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#fff',
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '1rem',
        boxSizing: 'border-box',
    },
    header: {
        marginTop: 0,
        marginBottom: '1rem',
    },
    contentArea: {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        minHeight: 0,
    },
    grayPanel: {
        backgroundColor: '#f9f9f9',
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '1rem',
        boxSizing: 'border-box',
        overflowY: 'auto',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
    },
    footer: {
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '1rem',
        backgroundColor: '#f0f0f0',
        borderTop: '1px solid #ccc',
        textAlign: 'center',
        zIndex: 1000,
    }
};

// Dark glassmorphism theme styles
const darkStyles = {
    pageContainer: {
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 180px)',
        width: '100%',
        boxSizing: 'border-box',
        padding: '20px 20px 0 20px',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)',
        minHeight: '100vh',
    },
    whiteCard: {
        maxWidth: '1800px',
        width: '100%',
        margin: '0 auto',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(30, 41, 59, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(20px)',
        borderRadius: '1rem',
        padding: '1.5rem',
        boxSizing: 'border-box',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    },
    header: {
        marginTop: 0,
        marginBottom: '1.5rem',
        fontSize: '1.5rem',
        fontWeight: 800,
        background: 'linear-gradient(to right, #c084fc, #6366f1)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
    },
    contentArea: {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        minHeight: 0,
    },
    grayPanel: {
        background: 'rgba(15, 23, 42, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '0.75rem',
        padding: '1rem',
        boxSizing: 'border-box',
        overflowY: 'auto',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        color: '#e2e8f0',
    },
    footer: {
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '1rem',
        background: 'rgba(15, 23, 42, 0.95)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        textAlign: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(10px)',
    }
};

/**
 * Main wrapper for the page content (above the footer).
 */
export const PageContainer = ({ children, darkMode = false }) => {
    const styles = darkMode ? darkStyles : lightStyles;
    return (
        <div style={styles.pageContainer}>
            {children}
        </div>
    );
};

/**
 * The Card component that centers and frames the content.
 */
export const ContentCard = ({ children, title, maxWidth = '900px', darkMode = false }) => {
    const styles = darkMode ? darkStyles : lightStyles;
    return (
        <div style={{ ...styles.whiteCard, maxWidth }}>
            {title && <h2 style={styles.header}>{title}</h2>}
            <div style={styles.contentArea}>
                {children}
            </div>
        </div>
    );
};

/**
 * The scrollable panel container.
 */
export const ScrollablePanel = ({ children, style = {}, darkMode = false }) => {
    const styles = darkMode ? darkStyles : lightStyles;
    return (
        <div style={{ ...styles.grayPanel, ...style }}>
            {children}
        </div>
    );
};

/**
 * The Fixed Footer at the bottom of the screen.
 */
export const FixedFooter = ({ children, darkMode = false }) => {
    const styles = darkMode ? darkStyles : lightStyles;
    return (
        <div style={styles.footer}>
            {children}
        </div>
    );
};

/**
 * A Fixed Floating Banner for key errors (e.g. Validation/Cron)
 * positioned at the top of the screen.
 */
export const FloatingErrorBanner = ({ children, isVisible, darkMode = false }) => {
    if (!isVisible) return null;

    const errorStyle = darkMode ? {
        position: 'fixed',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 2000,
        width: '80%',
        maxWidth: '600px',
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        borderRadius: '0.75rem',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        padding: '12px 16px',
        color: '#fca5a5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        backdropFilter: 'blur(10px)',
    } : {
        position: 'fixed',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 2000,
        width: '80%',
        maxWidth: '600px',
        backgroundColor: '#fee2e2',
        border: '1px solid #fca5a5',
        borderRadius: '6px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        padding: '12px 16px',
        color: '#991b1b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center'
    };

    return (
        <div style={errorStyle}>
            {children}
        </div>
    );
};
