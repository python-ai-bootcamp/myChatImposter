import React, { useState } from 'react';

// A custom collapsible field template for LLM Provider Config
// This wraps the entire field (including anyOf dropdown) in a collapsible section
// ONLY applies to the outer anyOf container, not the selected inner content
export function LLMProviderConfigFieldTemplate(props) {
    const [isOpen, setIsOpen] = useState(false);
    const { children, schema } = props;

    // Only apply the collapsible box if this field has anyOf in its schema
    // This means it's the outer container with the dropdown, not the inner selected content
    if (!schema || !schema.anyOf) {
        return children;
    }

    const containerStyle = {
        border: '1px solid #ddd',
        borderRadius: '4px',
        padding: '0.75rem',
        margin: '0.5rem 0',
        backgroundColor: '#fafafa',
    };

    const titleStyle = {
        margin: 0,
        padding: 0,
        cursor: 'pointer',
        textAlign: 'left',
        fontSize: '0.95rem',
        fontWeight: 600,
    };

    return (
        <div style={containerStyle}>
            <h4 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
                LLM Provider Config {isOpen ? '[-]' : '[+]'}
            </h4>
            {isOpen && (
                <div style={{ marginTop: '0.75rem', textAlign: 'left' }}>
                    {children}
                </div>
            )}
        </div>
    );
}
