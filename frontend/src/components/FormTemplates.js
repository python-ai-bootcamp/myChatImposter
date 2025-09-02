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

export function CustomFieldTemplate(props) {
  const { id, label, children, required, rawErrors = [], help, description, classNames } = props;

  // For items inside an array, we bypass the label/two-column layout in this template.
  // The layout is handled entirely by CustomArrayFieldTemplate.
  const isArrayItem = /_\d+$/.test(id);
  if (isArrayItem) {
    return children;
  }

  // Don't render a label for the top-level object title, it's handled by the ObjectFieldTemplate
  if (props.schema.type === 'object') {
      return children;
  }

  // A single, consistent layout for all other fields.
  const isLlmSelector = classNames && classNames.includes('llm-provider-selector');
  const rightColumnStyle = {
      width: '70%',
      boxSizing: 'border-box',
      paddingTop: '0.5rem',
      textAlign: 'left',
      paddingLeft: isLlmSelector ? '0' : undefined
  };

  return (
    <div className={classNames} style={{ display: 'flex', marginBottom: '1rem', alignItems: 'flex-start' }}>
      <label htmlFor={id} style={{ width: '30%', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0, paddingTop: '0.5rem' }}>
        {label}{required ? '*' : null}
      </label>
      <div style={rightColumnStyle}>
        {description}
        {children}
        {rawErrors.length > 0 && <ul>{rawErrors.map((error, i) => <li key={i} className="text-danger">{error}</li>)}</ul>}
        {help}
      </div>
    </div>
  );
}

export function CustomObjectFieldTemplate(props) {
  return (
    <fieldset style={{ border: 'none', padding: 0, margin: 0, width: '100%' }}>
      {/* Render the title of the object, aligned with the right column */}
      {props.title && (
         <div style={{ display: 'flex', marginBottom: '1rem', alignItems: 'center' }}>
            <div style={{ width: '30%', paddingRight: '1rem', boxSizing: 'border-box' }}></div>
            <div style={{ width: '70%', boxSizing: 'border-box' }}>
                <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>{props.title}</h3>
            </div>
         </div>
      )}

      {props.description}

      {/* Render the properties of the object */}
      {props.properties.map(element => (
        <div className="property-wrapper" key={element.content.key}>
          {element.content}
        </div>
      ))}
    </fieldset>
  );
}

export function CustomArrayFieldTemplate(props) {
    const btnStyle = {
        padding: '0.1rem 0.4rem',
        fontSize: '0.8rem',
        lineHeight: 1.2,
        border: '1px solid #ccc',
        borderRadius: '3px',
        cursor: 'pointer'
    };
    const disabledBtnStyle = {
        ...btnStyle,
        cursor: 'not-allowed',
        backgroundColor: '#f8f8f8',
        color: '#ccc',
    };

    return (
      <div>
        {props.items &&
          props.items.map(element => (
            // Use baseline alignment for better vertical alignment of text input and buttons
            <div key={element.key} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'baseline' }}>
              <span style={{ marginRight: '0.5rem', paddingTop: '0.5rem' }}>•</span>
              {/* This div no longer expands, so the buttons will be right next to the input */}
              <div>{element.children}</div>
              <div style={{ marginLeft: '0.5rem', display: 'flex', gap: '0.3rem' }}>
                <button
                    type="button"
                    onClick={element.onReorderClick(element.index, element.index - 1)}
                    style={element.hasMoveUp ? btnStyle : disabledBtnStyle}
                    disabled={!element.hasMoveUp}
                >
                    ↑
                </button>
                <button
                    type="button"
                    onClick={element.onReorderClick(element.index, element.index + 1)}
                    style={element.hasMoveDown ? btnStyle : disabledBtnStyle}
                    disabled={!element.hasMoveDown}
                >
                    ↓
                </button>
                <button
                    type="button"
                    onClick={element.onDropIndexClick(element.index)}
                    style={element.hasRemove ? btnStyle : disabledBtnStyle}
                    disabled={!element.hasRemove}
                >
                    -
                </button>
              </div>
            </div>
          ))}

        {props.canAdd && (
          <button type="button" onClick={props.onAddClick} style={{ ...btnStyle, padding: '0.3rem 0.6rem', marginTop: '0.5rem' }}>
            + Add
          </button>
        )}
      </div>
    );
  }
