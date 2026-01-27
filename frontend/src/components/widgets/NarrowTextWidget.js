import React from 'react';

// A narrow text input widget for compact inline fields
export function NarrowTextWidget(props) {
    return (
        <input
            type="text"
            id={props.id}
            value={props.value || ''}
            required={props.required}
            onChange={(event) => props.onChange(event.target.value)}
            style={{ width: '80px' }}
        />
    );
}
