import React from 'react';

// Stable widget definitions - defined outside component to prevent re-creation on re-render
export const ReadOnlyTextWidget = (props) => {
    return (
        <input
            type="text"
            value={props.value || ''}
            disabled
            style={{
                width: '90px',
                backgroundColor: 'rgba(15, 23, 42, 0.4)', // Dark disabled background
                color: '#94a3b8', // Slate-400
                fontSize: '0.45rem',
                padding: '2px 4px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '4px'
            }}
            title="Auto-filled from group selection"
        />
    );
};
