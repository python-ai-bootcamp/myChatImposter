import React from 'react';

// A text widget with configurable width via ui:options.width
export function SizedTextWidget(props) {
    const width = props.options?.width || '150px';
    return (
        <input
            type="text"
            id={props.id}
            value={props.value || ''}
            required={props.required}
            onChange={(event) => props.onChange(event.target.value)}
            style={{ width }}
        />
    );
}
