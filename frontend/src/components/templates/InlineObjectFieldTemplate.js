import React from 'react';

// An inline compact object template for array items like PeriodicGroupTrackingConfig
// Renders all fields on a single line with label:input pairs and tooltip descriptions
export function InlineObjectFieldTemplate(props) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {props.properties.map(element => {
                const schema = element.content.props.schema;
                const uiSchema = element.content.props.uiSchema || {};
                const description = schema?.description || '';
                // Use ui:title from uiSchema if available, otherwise fall back to schema title
                const label = uiSchema['ui:title'] || schema?.title || element.name;
                // Note: element.content.props.required available if needed

                return (
                    <div key={element.content.key} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <label
                            htmlFor={element.content.props.idSchema.$id}
                            title={description}
                            style={{
                                fontSize: '0.85rem',
                                cursor: description ? 'help' : 'default',
                                textDecoration: description ? 'underline dotted' : 'none',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            {label}
                        </label>
                        {element.content}
                    </div>
                );
            })}
        </div>
    );
}
