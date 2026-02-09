import React, { useState, useEffect, useRef } from 'react';

export function CollapsibleObjectFieldTemplate(props) {
    const defaultOpen = props.uiSchema?.['ui:options']?.defaultOpen || false;
    const [isOpen, setIsOpen] = useState(defaultOpen);
    const { cronErrors, saveAttempt, scrollToErrorTrigger } = props.registry?.formContext || props.formContext || {};
    const prevSaveAttempt = useRef(saveAttempt);
    const prevTrigger = useRef(scrollToErrorTrigger);

    // Check if this section contains the periodic_group_tracking field
    const containsTracking = props.properties.some(p => p.name === 'periodic_group_tracking');

    useEffect(() => {
        // Auto-expand when saveAttempt increments OR trigger changes and there are cron errors
        if (saveAttempt !== prevSaveAttempt.current || scrollToErrorTrigger !== prevTrigger.current) {
            if (containsTracking && cronErrors && cronErrors.length > 0) {
                const hasErrors = cronErrors.some(e => e);
                if (hasErrors) {
                    setIsOpen(true);
                }
            }
            prevSaveAttempt.current = saveAttempt;
            prevTrigger.current = scrollToErrorTrigger;
        }
    }, [saveAttempt, scrollToErrorTrigger, containsTracking, cronErrors]);

    // Dark glassmorphism container style
    const containerStyle = {
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '0.75rem',
        padding: '1rem',
        margin: '1rem 0',
        background: 'rgba(30, 41, 59, 0.6)',
        backdropFilter: 'blur(10px)',
    };

    const titleStyle = {
        margin: 0,
        padding: 0,
        cursor: 'pointer',
        textAlign: 'left',
        color: '#c084fc',
        fontWeight: 600,
    };

    return (
        <div style={containerStyle}>
            <h3 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
                {props.title} {isOpen ? '[-]' : '[+]'}
            </h3>
            {isOpen && (
                <div style={{ marginTop: '1rem', color: '#e2e8f0' }}>
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
