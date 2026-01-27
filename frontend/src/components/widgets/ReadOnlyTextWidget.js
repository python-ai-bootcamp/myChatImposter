import React from 'react';

// Stable widget definitions - defined outside component to prevent re-creation on re-render
export const ReadOnlyTextWidget = (props) => {
    return (
        <input
            type="text"
            value={props.value || ''}
            disabled
            style={{ width: '90px', backgroundColor: '#f5f5f5', color: '#666', fontSize: '0.45rem', padding: '2px 4px' }}
            title="Auto-filled from group selection"
        />
    );
};
