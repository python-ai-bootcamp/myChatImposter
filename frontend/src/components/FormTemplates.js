import React, { useState } from 'react';

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
  const { id, label, children, required, rawErrors = [], help, description, classNames, schema, uiSchema } = props;

  // HACK: This is a very specific fix to prevent a duplicate label for the `provider_config` field.
  // The rjsf oneOf widget renders its own label, and so does our template, causing a duplicate.
  // This checks for the specific ID of that field and if it's the inner one rendered as an object.
  if (id === 'root_llm_bot_config_llm_provider_config_provider_config' && classNames.includes('field-object')) {
    return children;
  }

  if (uiSchema && uiSchema['ui:options']?.hidden) {
    return null;
  }

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
      boxSizing: 'border-box',
      textAlign: 'left',
      display: 'table-cell',
      width: '100%'
  };

  return (
    <>
      <div className={classNames} style={{ display: 'table-row' }}>
        <label htmlFor={id} style={{ display: 'table-cell', whiteSpace: 'nowrap', verticalAlign: 'top', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0 }}>
          {label}{required ? '*' : null}
        </label>
        <div style={rightColumnStyle}>
          {description}
          {children}
          {rawErrors.length > 0 && <ul>{rawErrors.map((error, i) => <li key={i} className="text-danger">{error}</li>)}</ul>}
          {help}
        </div>
      </div>
    </>
  );
}

export function CollapsibleObjectFieldTemplate(props) {
  const [isOpen, setIsOpen] = useState(false);

  const containerStyle = {
    border: '1px solid #ccc',
    borderRadius: '4px',
    padding: '1rem',
    margin: '1rem 0',
    backgroundColor: '#fff',
  };

  const titleStyle = {
    margin: 0,
    padding: 0,
    cursor: 'pointer',
    textAlign: 'left',
  };

  return (
    <div style={containerStyle}>
      <h3 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
        {props.title} {isOpen ? '[-]' : '[+]'}
      </h3>
      {isOpen && (
        <div style={{marginTop: '1rem'}}>
          {props.description}
          {props.properties.map(element => (
            <React.Fragment key={element.content.key}>
              {element.content}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}

export function CustomObjectFieldTemplate(props) {
  // A more robust way to detect the provider settings objects that need special styling.
  const isChatProviderSettings = props.properties.some(p => p.name === 'allow_group_messages');
  const isLlmProviderSettings = props.uiSchema['ui:options']?.box === 'LlmProviderSettings';
  const shouldHaveBorder = isChatProviderSettings || isLlmProviderSettings;

  const fieldsetStyle = {
    border: shouldHaveBorder ? '1px solid #ccc' : 'none',
    borderRadius: '4px',
    padding: shouldHaveBorder ? '1rem' : '0',
    margin: 0,
    width: '100%',
    marginTop: shouldHaveBorder ? '0.5rem' : '0',
    display: 'table',
    borderCollapse: 'collapse'
  };

  // Determine the correct title to display.
  let title = props.title;
  if (isLlmProviderSettings) {
    title = 'LlmProviderSettings';
  } else if (isChatProviderSettings) {
    title = 'ChatProviderSettings';
  }

  // Hide the title for the inner oneOf selection, but show our custom one.
  // This is the definitive fix: explicitly check for the title we want to hide.
  const isLlmModeTitle = props.title === 'Llm Mode';
  const shouldShowTitle = !isLlmModeTitle && ((title && shouldHaveBorder) || (props.title && !isLlmProviderSettings && props.title !== 'Respond Using Llm'));


  return (
    <fieldset style={fieldsetStyle}>
      {shouldShowTitle && (
        <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', textAlign: 'left' }}>
            {title}
        </h3>
      )}

      {props.description}
      {props.properties.map(element => (
        <React.Fragment key={element.content.key}>
          {element.content}
        </React.Fragment>
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
                <span style={{ marginRight: '0.5rem' }}>•</span>
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
