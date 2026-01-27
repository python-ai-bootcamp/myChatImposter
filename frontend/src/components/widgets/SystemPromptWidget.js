import React from 'react';

// A textarea widget for the system prompt with fixed dimensions
export function SystemPromptWidget(props) {
    return (
        <textarea
            id={props.id}
            value={props.value || ''}
            required={props.required}
            onChange={(event) => props.onChange(event.target.value)}
            style={{
                width: '290px',
                height: '150px',
                resize: 'both',
                fontFamily: 'inherit',
                fontSize: 'inherit',
                padding: '4px'
            }}
        />
    );
}
