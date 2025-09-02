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

  // This is the new logic to handle the special provider config sections.
  // We identify them by their top-level ID and apply a border and indented title.
  const isProviderContainer = id === 'root_chat_provider_config' || id === 'root_llm_provider_config';
  if (isProviderContainer) {
    return (
        <div className={classNames} style={{ display: 'flex', marginBottom: '1rem', alignItems: 'flex-start' }}>
            {/* Empty left column to maintain alignment */}
            <div style={{ width: '30%', paddingRight: '1rem' }}></div>
            {/* Right column contains the border, title, and the actual object fields */}
            <div style={{ width: '70%', border: '1px solid #ccc', borderRadius: '4px', padding: '1rem' }}>
                <h3 style={{ marginTop: 0, paddingTop: 0 }}>{label}</h3>
                {children}
            </div>
        </div>
    )
  }

  // Don't render a label for the top-level object title, it's handled by the ObjectFieldTemplate
  if (props.schema.type === 'object') {
      return children;
  }

  // A single, consistent layout for all other fields.
  const rightColumnStyle = {
      width: '70%',
      boxSizing: 'border-box',
      paddingTop: '0.5rem',
      textAlign: 'left',
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

// This template is now much simpler. It just renders the properties.
// The border and title are handled by the parent CustomFieldTemplate.
export function CustomObjectFieldTemplate(props) {
  return (
    <fieldset style={{ border: 'none', padding: 0, margin: 0, width: '100%' }}>
      {props.description}
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
      <div style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '1rem' }}>
        {props.items &&
          props.items.map(element => (
            <div key={element.key} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'baseline' }}>
                <span style={{ marginRight: '0.5rem', paddingTop: '0.5rem' }}>•</span>
                {/* This inner flex container groups the input and buttons together */}
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                    {/* The input field itself (no flex: 1) */}
                    <div>{element.children}</div>
                    {/* The buttons */}
                    <div style={{ display: 'flex', gap: '0.3rem' }}>
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
