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

  // This is the new logic to handle the special chat provider config section.
  // It creates an indented title and wraps the content in a border.
  if (id === 'root_chat_provider_config') {
    return (
        <div className={classNames} style={{ display: 'flex', marginBottom: '1rem', alignItems: 'flex-start' }}>
            {/* Empty left column to maintain alignment */}
            <div style={{ width: '30%', paddingRight: '1rem' }}></div>
            {/* Right column contains the title AND the bordered box */}
            <div style={{ width: '70%' }}>
                <h3 style={{ marginTop: 0, paddingTop: 0, marginBottom: '0.5rem' }}>{label}</h3>
                <div style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '1rem' }}>
                    {children}
                </div>
            </div>
        </div>
    );
  }

  // Don't render a label for other top-level objects, it's handled by the ObjectFieldTemplate
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
  // This is the logic from before the last change.
  // It correctly applies a border ONLY to the LLM provider's inner settings object.
  const hasApiKey = props.properties.some(p => p.name === 'api_key');
  const fieldsetStyle = {
    border: hasApiKey ? '1px solid #ccc' : 'none',
    borderRadius: hasApiKey ? '4px' : '0',
    padding: hasApiKey ? '1rem' : '0',
    margin: 0,
    width: '100%'
  };

  // This is the fix for the "double title" issue.
  // We don't render a title for the main chat_provider_config object,
  // because the CustomFieldTemplate is already rendering it.
  const isChatProviderObject = props.idSchema.$id === 'root_chat_provider_config';


  return (
    <fieldset style={fieldsetStyle}>
      {/* Render the title of the object, aligned with the right column, but not for the chat provider object */}
      {props.title && !isChatProviderObject && (
         <div style={{ display: 'flex', marginBottom: '1rem', alignItems: 'center' }}>
            <div style={{ width: '30%', paddingRight: '1rem', boxSizing: 'border-box' }}></div>
            <div style={{ width: '70%', boxSizing: 'border-box' }}>
                <h3 style={{ margin: 0, padding: 0, borderBottom: hasApiKey ? 'none' : '1px solid #eee', paddingBottom: '0.5rem' }}>{props.title}</h3>
            </div>
         </div>
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
