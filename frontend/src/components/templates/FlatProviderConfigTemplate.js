import React from 'react';

// A flat object template that renders children without the panel-body wrapper
// Used for llm_provider_config.provider_config to flatten the oneOf dropdown alignment
export function FlatProviderConfigTemplate(props) {
    // Separate boolean fields from other fields - booleans render outside the table
    const tableFields = props.properties.filter(element => {
        const schema = element.content?.props?.schema;
        return schema?.type !== 'boolean';
    });
    const booleanFields = props.properties.filter(element => {
        const schema = element.content?.props?.schema;
        return schema?.type === 'boolean';
    });

    return (
        <>
            <div style={{ display: 'table', width: '100%', borderCollapse: 'collapse' }}>
                {tableFields.map(element => (
                    <React.Fragment key={element.content.key}>
                        {element.content}
                    </React.Fragment>
                ))}
            </div>
            {booleanFields.map(element => (
                <React.Fragment key={element.content.key}>
                    {element.content}
                </React.Fragment>
            ))}
        </>
    );
}
