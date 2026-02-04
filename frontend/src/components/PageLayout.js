import React from 'react';

// Common styles to ensure consistency
const styles = {
    pageContainer: {
        display: 'flex',
        flexDirection: 'column',
        // Accounts for footer height (approx 80px) + bottom gap (20px) + top padding (20px)
        // We use a safe calculation to ensure the white card never touches the bottom buttons
        height: 'calc(100vh - 180px)',
        width: '100%',
        boxSizing: 'border-box',
        padding: '20px 20px 0 20px',
    },
    whiteCard: {
        maxWidth: '1800px', // Large enough for split view
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
        overflow: 'hidden', // Prevent outer scroll
        minHeight: 0, // Flexbox overflow fix
    },
    grayPanel: {
        backgroundColor: '#f9f9f9',
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '1rem',
        boxSizing: 'border-box',
        overflowY: 'auto', // THIS is where the scrolling happens
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
    },
    footer: {
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '1rem', // approx 60-80px total height
        backgroundColor: '#f0f0f0',
        borderTop: '1px solid #ccc',
        textAlign: 'center',
        zIndex: 1000,
    }
};

/**
 * Main wrapper for the page content (above the footer).
 */
export const PageContainer = ({ children }) => (
    <div style={styles.pageContainer}>
        {children}
    </div>
);

/**
 * The White Card component that centers and frames the content.
 */
export const ContentCard = ({ children, title, maxWidth = '900px' }) => (
    <div style={{ ...styles.whiteCard, maxWidth }}>
        {title && <h2 style={styles.header}>{title}</h2>}
        <div style={styles.contentArea}>
            {children}
        </div>
    </div>
);

/**
 * The "Inner Gray Cubish Thingy" - a scrollable container.
 */
export const ScrollablePanel = ({ children, style = {} }) => (
    <div style={{ ...styles.grayPanel, ...style }}>
        {children}
    </div>
);

/**
 * The Fixed Footer at the bottom of the screen.
 */
export const FixedFooter = ({ children }) => (
    <div style={styles.footer}>
        {children}
    </div>
);
