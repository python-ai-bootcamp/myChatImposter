import React, { useState, useEffect, useRef } from 'react';

export function CollapsibleObjectFieldTemplate(props) {
    const defaultOpen = props.uiSchema?.['ui:options']?.defaultOpen || false;
    const [isOpen, setIsOpen] = useState(defaultOpen);
    const { cronErrors, saveAttempt } = props.registry?.formContext || props.formContext || {};
    const prevSaveAttempt = useRef(saveAttempt);

    // Check if this section contains the periodic_group_tracking field
    const containsTracking = props.properties.some(p => p.name === 'periodic_group_tracking');

    useEffect(() => {
        // Auto-expand only when saveAttempt increments (indicating a new save click)
        // and there are actual errors.
        if (saveAttempt !== prevSaveAttempt.current) {
            if (containsTracking && cronErrors && cronErrors.length > 0) {
                const hasErrors = cronErrors.some(e => e);
                if (hasErrors) {
                    setIsOpen(true);
                }
            }
            prevSaveAttempt.current = saveAttempt;
        }
    }, [saveAttempt, containsTracking, cronErrors]);

    const containerStyle = {
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '1rem',
        margin: '1rem 0',
        backgroundColor: '#fff',
    };

    const titleStyle = {
        margin: 0,
        padding: 0,
        cursor: 'pointer',
        textAlign: 'left',
    };

    return (
        <div style={containerStyle}>
            <h3 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
                {props.title} {isOpen ? '[-]' : '[+]'}
            </h3>
            {isOpen && (
                <div style={{ marginTop: '1rem' }}>
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
