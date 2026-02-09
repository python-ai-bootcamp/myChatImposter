import React, { useState, useEffect, useRef } from 'react';

// Nested collapsible object template for sub-sections within main sections
export function NestedCollapsibleObjectFieldTemplate(props) {
    const { cronErrors, saveAttempt, scrollToErrorTrigger } = props.registry?.formContext || props.formContext || {};
    const prevSaveAttempt = useRef(saveAttempt);
    const prevTrigger = useRef(scrollToErrorTrigger);

    // Check if this section contains tracked_groups field (for periodic_group_tracking feature)
    const containsTrackedGroups = props.properties.some(p => p.name === 'tracked_groups');

    // Force open on mount if we have errors and the trigger was recently fired (simplified: just if we have errors)
    // We assume if scrollToErrorTrigger > 0, the user wants us to find errors.
    const defaultOpen = props.uiSchema?.['ui:options']?.defaultOpen || false;
    const shouldStartOpen = defaultOpen || (containsTrackedGroups && cronErrors && cronErrors.some(e => e) && scrollToErrorTrigger > 0);
    const [isOpen, setIsOpen] = useState(shouldStartOpen);

    useEffect(() => {
        // Auto-expand when saveAttempt increments OR trigger changes and there are cron errors
        if (saveAttempt !== prevSaveAttempt.current || scrollToErrorTrigger !== prevTrigger.current) {
            if (containsTrackedGroups && cronErrors && cronErrors.length > 0) {
                const hasErrors = cronErrors.some(e => e);
                if (hasErrors) {
                    setIsOpen(true);
                }
            }
            prevSaveAttempt.current = saveAttempt;
            prevTrigger.current = scrollToErrorTrigger;
        }
    }, [saveAttempt, scrollToErrorTrigger, containsTrackedGroups, cronErrors]);

    // Dark glassmorphism nested container style
    const containerStyle = {
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '0.5rem',
        padding: '0.75rem',
        margin: '0.5rem 0',
        background: 'rgba(15, 23, 42, 0.5)',
    };

    const titleStyle = {
        margin: 0,
        padding: 0,
        cursor: 'pointer',
        textAlign: 'left',
        fontSize: '0.95rem',
        fontWeight: 600,
        color: '#a5b4fc',
    };

    return (
        <div style={containerStyle}>
            <h4 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
                {props.title} {isOpen ? '[-]' : '[+]'}
            </h4>
            {isOpen && (
                <div style={{ marginTop: '0.75rem', color: '#e2e8f0' }}>
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
