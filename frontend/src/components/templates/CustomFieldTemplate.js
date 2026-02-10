import React from 'react';

export function CustomFieldTemplate(props) {
    const { id, label, children, rawErrors = [], help, description, classNames, schema, uiSchema } = props;

    // Hide the inner LLMProviderConfig object box (the one that creates duplicate nested box)
    // This matches the inner object selected by the anyOf dropdown
    if (id && id.includes('llm_provider_config') && classNames && classNames.includes('field-object')) {
        if (!id.endsWith('configurations_llm_provider_config')) {
            return children;
        }
    }

    // Hide API Key Source field (it's redundant with the oneOf dropdown)
    if (id && id.includes('api_key_source')) {
        return null;
    }

    // Render API Key Source dropdown with proper table-row layout matching other fields
    // This needs to output the same structure as the standard CustomFieldTemplate for consistency
    if (id && id.includes('provider_config__oneof_select')) {
        return (
            <div className={classNames} style={{ display: 'table-row', textAlign: 'left' }}>
                <label style={{ display: 'table-cell', whiteSpace: 'nowrap', verticalAlign: 'top', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0 }}>
                    API Key Source
                </label>
                <div style={{ boxSizing: 'border-box', textAlign: 'left', display: 'table-cell', width: '100%' }}>
                    {children}
                </div>
            </div>
        );
    }

    // Flatten the provider_config field structure - render children directly
    if (id && (id.endsWith('chat_provider_config_provider_config') || id.endsWith('llm_provider_config_provider_config'))) {
        return children;
    }

    // Indent API Key field to align with Reasoning Effort dropdown
    // Render with empty first cell so it appears in the right column
    if (id && id.endsWith('provider_config_api_key')) {
        return (
            <div style={{ display: 'table-row' }}>
                <div style={{ display: 'table-cell' }}></div>
                <div style={{ display: 'table-cell', textAlign: 'left', width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="custom-label-text" style={{ whiteSpace: 'nowrap' }}>{label}</span>
                        {children}
                    </div>
                </div>
            </div>
        );
    }

    // Also hide old special handling that created nested boxes
    if (id === 'root_llm_bot_config_llm_provider_config_provider_config') {
        return children;
    }

    if (uiSchema && uiSchema['ui:options']?.hidden) {
        return null;
    }

    // For items inside an array, we bypass the label/two-column layout in this template.
    // The layout is handled entirely by CustomArrayFieldTemplate.
    const isArrayItem = /_\d+$/.test(id);
    if (isArrayItem) {
        return children;
    }

    // For object containers, we let the ObjectFieldTemplate handle the title and layout.
    if (schema.type === 'object') {
        return children;
    }

    // Special handling for boolean fields - pure flex layout to avoid table-cell centering issues
    if (schema.type === 'boolean') {
        return (
            <div className={classNames} style={{
                display: 'flex',
                flexDirection: 'row',
                justifyContent: 'flex-start',
                alignItems: 'center',
                gap: '1rem',
                marginTop: '0.5rem',
                marginBottom: '0.5rem',
                textAlign: 'left'
            }}>
                <span className="custom-label-text" style={{ whiteSpace: 'nowrap', minWidth: '110px' }}>
                    {label}
                </span>
                <input
                    type="checkbox"
                    id={id}
                    checked={typeof props.formData === 'undefined' ? false : props.formData}
                    onChange={(e) => props.onChange(e.target.checked)}
                    style={{ margin: 0, marginLeft: '18px' }}
                />
            </div>
        );
    }

    // A single, consistent layout for all other fields.
    const rightColumnStyle = {
        boxSizing: 'border-box',
        textAlign: 'left',
        display: 'table-cell',
        width: '100%'
    };

    return (
        <>
            <div className={classNames} style={{ display: 'table-row' }}>
                <label htmlFor={id} style={{ display: 'table-cell', whiteSpace: 'nowrap', verticalAlign: 'top', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0 }}>
                    {label}
                </label>
                <div style={rightColumnStyle}>
                    {description}
                    {children}
                    {rawErrors.length > 0 && <ul>{rawErrors.map((error, i) => <li key={i} className="text-danger">{error}</li>)}</ul>}
                    {help}
                </div>
            </div>
        </>
    );
}
