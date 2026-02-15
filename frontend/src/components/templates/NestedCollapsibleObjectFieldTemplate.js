import React, { useState, useEffect, useRef } from 'react';

// Nested collapsible object template for sub-sections within main sections
export function NestedCollapsibleObjectFieldTemplate(props) {
    const { cronErrors, saveAttempt, scrollToErrorTrigger, goToFeaturesTrigger } = props.registry?.formContext || props.formContext || {};
    const prevSaveAttempt = useRef(saveAttempt);
    const prevTrigger = useRef(scrollToErrorTrigger);
    const prevGoToFeatures = useRef(goToFeaturesTrigger);

    // Check if this section contains tracked_groups field (for periodic_group_tracking feature)
    const containsTrackedGroups = props.properties.some(p => p.name === 'tracked_groups');
    // Check if this is a feature sub-section (has an 'enabled' property)
    const isFeatureSubSection = props.properties.some(p => p.name === 'enabled');
    // Check if this feature is actually enabled (ticked)
    const isFeatureEnabled = isFeatureSubSection && props.formData?.enabled === true;

    // Initialize highlight at mount if trigger is active and feature is enabled
    const [highlightEnabled, setHighlightEnabled] = useState(isFeatureEnabled && goToFeaturesTrigger > 0);

    // Auto-clear highlight after animation completes
    useEffect(() => {
        if (highlightEnabled) {
            const timer = setTimeout(() => setHighlightEnabled(false), 2500);
            return () => clearTimeout(timer);
        }
    }, [highlightEnabled]);

    // Force open on mount if we have errors and the trigger was recently fired (simplified: just if we have errors)
    // We assume if scrollToErrorTrigger > 0, the user wants us to find errors.
    // Also open immediately if goToFeaturesTrigger > 0 (so sub-sections expand simultaneously with parent)
    const defaultOpen = props.uiSchema?.['ui:options']?.defaultOpen || false;
    const shouldStartOpen = defaultOpen
        || (containsTrackedGroups && cronErrors && cronErrors.some(e => e) && scrollToErrorTrigger > 0)
        || (isFeatureSubSection && goToFeaturesTrigger > 0);
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

    // Auto-expand and highlight when "Go to Features" is clicked (for already-mounted components)
    useEffect(() => {
        if (goToFeaturesTrigger !== prevGoToFeatures.current) {
            if (isFeatureSubSection) {
                setIsOpen(true);
                if (isFeatureEnabled) {
                    setHighlightEnabled(true);
                }
            }
            prevGoToFeatures.current = goToFeaturesTrigger;
        }
    }, [goToFeaturesTrigger, isFeatureSubSection, isFeatureEnabled]);

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
            <style>{`
                @keyframes featureHighlightPulse {
                    0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
                    40% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.4); }
                    80% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
                }
                .feature-highlight-enabled .inline-checkbox-field {
                    animation: featureHighlightPulse 0.8s ease-out 3;
                    border-radius: 6px;
                    outline: 2px solid #ef4444;
                    outline-offset: 2px;
                }
            `}</style>
            <h4 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
                {props.title} {isOpen ? '[-]' : '[+]'}
            </h4>
            {isOpen && (
                <div
                    style={{ marginTop: '0.75rem', color: '#e2e8f0' }}
                    className={highlightEnabled ? 'feature-highlight-enabled' : ''}
                >
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
