import React from 'react';

// A custom widget for checkboxes that only renders the input element.
// The label is handled by the CustomFieldTemplate.
export function CustomCheckboxWidget(props) {
    return (
        <input
            type="checkbox"
            id={props.id}
            checked={typeof props.value === 'undefined' ? false : props.value}
            required={props.required}
            onChange={(event) => props.onChange(event.target.checked)}
            style={{ margin: 0 }}
        />
    );
}
