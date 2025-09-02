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
  const { id, label, children, required, rawErrors = [], help, description, classNames, schema } = props;

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

export function CustomObjectFieldTemplate(props) {
  // Conditionally apply border for the inner provider settings objects.
  const hasApiKey = props.properties.some(p => p.name === 'api_key');
  const hasGroupMessages = props.properties.some(p => p.name === 'allow_group_messages');
  const shouldHaveBorder = hasApiKey || hasGroupMessages;

  const fieldsetStyle = {
    border: shouldHaveBorder ? '1px solid #ccc' : 'none',
    borderRadius: shouldHaveBorder ? '4px' : '0',
    padding: shouldHaveBorder ? '1rem' : '0',
    margin: 0,
    width: '100%',
    // Add margin if there's a border, to space it from the title
    marginTop: shouldHaveBorder ? '0.5rem' : '0'
  };

  return (
    <fieldset style={fieldsetStyle}>
      {/* Render the title fully left-aligned with a separator line */}
      {props.title && (
        <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', textAlign: 'left' }}>
            {props.title}
        </h3>
      )}

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
        {props.title && (
            <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', textAlign: 'left' }}>
                {props.title}
            </h3>
        )}
        {props.items &&
          props.items.map(element => (
            <div key={element.key} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'baseline' }}>
                <span style={{ marginRight: '0.5rem', paddingTop: '0.5rem' }}>•</span>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                    <div>{element.children}</div>
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
