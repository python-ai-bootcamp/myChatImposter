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

  if (uiSchema && uiSchema['ui:options']?.hidden) {
    return null;
  }

  if (id.includes('__oneof_select')) {
    return children;
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
    display: 'block', // Changed from 'table' to 'block'
    borderCollapse: 'collapse'
  };

  let title = props.title;
  if (isLlmProviderSettings) {
    title = 'LlmProviderSettings';
  } else if (isChatProviderSettings) {
    title = 'ChatProviderSettings';
  }

  const shouldShowTitle = (title && shouldHaveBorder) || (props.title && !isLlmProviderSettings && props.title !== 'Respond Using Llm');

  let oneOfSelect = null;
  let otherProperties = [];

  if (isLlmProviderSettings) {
    // Separate the oneOf select from the other properties.
    props.properties.forEach(element => {
      if (element.content.key.includes('__oneof_select')) {
        oneOfSelect = element.content;
      } else {
        otherProperties.push(element);
      }
    });
  } else {
    otherProperties = props.properties;
  }

  return (
    <fieldset style={fieldsetStyle}>
      {shouldShowTitle && (
        <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', textAlign: 'left' }}>
          {title}
        </h3>
      )}

      {/* Render the oneOf select right after the title if it exists */}
      {oneOfSelect}

      {props.description}
      <div style={{display: 'table', width: '100%'}}>
        {otherProperties.map(element => (
          <React.Fragment key={element.content.key}>
            {element.content}
          </React.Fragment>
        ))}
      </div>
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
