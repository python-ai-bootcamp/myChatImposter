import React, { useState, useEffect, useRef } from 'react';

// Nested collapsible object template for sub-sections within main sections
export function NestedCollapsibleObjectFieldTemplate(props) {
    const [isOpen, setIsOpen] = useState(false);
    const { cronErrors, saveAttempt } = props.registry?.formContext || props.formContext || {};
    const prevSaveAttempt = useRef(saveAttempt);

    // Check if this section contains tracked_groups field (for periodic_group_tracking feature)
    const containsTrackedGroups = props.properties.some(p => p.name === 'tracked_groups');

    useEffect(() => {
        // Auto-expand when saveAttempt increments and there are cron errors
        if (saveAttempt !== prevSaveAttempt.current) {
            if (containsTrackedGroups && cronErrors && cronErrors.length > 0) {
                const hasErrors = cronErrors.some(e => e);
                if (hasErrors) {
                    setIsOpen(true);
                }
            }
            prevSaveAttempt.current = saveAttempt;
        }
    }, [saveAttempt, containsTrackedGroups, cronErrors]);

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
                {props.title} {isOpen ? '[-]' : '[+]'}
            </h4>
            {isOpen && (
                <div style={{ marginTop: '0.75rem' }}>
                    {props.description}
                    {props.properties.map(element => (
                        <React.Fragment key={element.content.key}>
                            {element.content}
                        </React.Fragment>
                    ))}
                </div>
            )}
        </div>
    );
}
