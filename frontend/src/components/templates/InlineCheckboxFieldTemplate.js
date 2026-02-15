import React from 'react';

// An inline checkbox field template - label and checkbox on same line
export function InlineCheckboxFieldTemplate(props) {
    const { id, label, children, required } = props;
    return (
        <div className="inline-checkbox-field" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
            <label htmlFor={id} style={{ margin: 0 }}>
                {label}{required && '*'}
            </label>
            {children}
        </div>
    );
}
