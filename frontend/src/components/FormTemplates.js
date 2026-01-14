import React, { useState, useEffect, useRef } from 'react';

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

// A textarea widget for the system prompt with fixed dimensions
export function SystemPromptWidget(props) {
  return (
    <textarea
      id={props.id}
      value={props.value || ''}
      required={props.required}
      onChange={(event) => props.onChange(event.target.value)}
      style={{
        width: '191px',
        height: '240px',
        resize: 'both',
        fontFamily: 'inherit',
        fontSize: 'inherit',
        padding: '4px'
      }}
    />
  );
}

// An inline checkbox field template - label and checkbox on same line
export function InlineCheckboxFieldTemplate(props) {
  const { id, label, children, required } = props;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
      <label htmlFor={id} style={{ margin: 0 }}>
        {label}{required && '*'}
      </label>
      {children}
    </div>
  );
}

// A custom collapsible field template for LLM Provider Config
// This wraps the entire field (including anyOf dropdown) in a collapsible section
// ONLY applies to the outer anyOf container, not the selected inner content
export function LLMProviderConfigFieldTemplate(props) {
  const [isOpen, setIsOpen] = useState(false);
  const { children, schema } = props;

  // Only apply the collapsible box if this field has anyOf in its schema
  // This means it's the outer container with the dropdown, not the inner selected content
  if (!schema || !schema.anyOf) {
    return children;
  }

  const containerStyle = {
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '0.75rem',
    margin: '0.5rem 0',
    backgroundColor: '#fafafa',
  };

  const titleStyle = {
    margin: 0,
    padding: 0,
    cursor: 'pointer',
    textAlign: 'left',
    fontSize: '0.95rem',
    fontWeight: 600,
  };

  return (
    <div style={containerStyle}>
      <h4 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
        LLM Provider Config {isOpen ? '[-]' : '[+]'}
      </h4>
      {isOpen && (
        <div style={{ marginTop: '0.75rem', textAlign: 'left' }}>
          {children}
        </div>
      )}
    </div>
  );
}



export function CustomFieldTemplate(props) {
  const { id, label, children, required, rawErrors = [], help, description, classNames, schema, uiSchema } = props;

  // Hide the inner LLMProviderConfig object box (the one that creates duplicate nested box)
  // This matches the inner object selected by the anyOf dropdown
  if (id && id.includes('llm_provider_config') && classNames && classNames.includes('field-object')) {
    if (!id.endsWith('configurations_llm_provider_config')) {
      return children;
    }
  }

  // Hide API Key Source field (it's redundant with the oneOf dropdown)
  if (id && id.includes('api_key_source')) {
    return null;
  }

  // Add "API Key Source" label for the oneOf dropdown (API Key From User Input/Environment)
  if (id && id.includes('provider_config__oneof_select')) {
    return (
      <div style={{ display: 'table-row' }}>
        <label style={{ display: 'table-cell', whiteSpace: 'nowrap', verticalAlign: 'top', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0 }}>
          API Key Source
        </label>
        <div style={{ display: 'table-cell', textAlign: 'left', width: '100%' }}>
          {children}
        </div>
      </div>
    );
  }

  // Also hide old special handling that created nested boxes
  if (id === 'root_llm_bot_config_llm_provider_config_provider_config') {
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
          {label}
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
  const { cronErrors, saveAttempt } = props.registry?.formContext || props.formContext || {};
  const prevSaveAttempt = useRef(saveAttempt);

  // Check if this section contains the periodic_group_tracking field
  const containsTracking = props.properties.some(p => p.name === 'periodic_group_tracking');

  useEffect(() => {
    // Auto-expand only when saveAttempt increments (indicating a new save click)
    // and there are actual errors.
    if (saveAttempt !== prevSaveAttempt.current) {
      if (containsTracking && cronErrors && cronErrors.length > 0) {
        const hasErrors = cronErrors.some(e => e);
        if (hasErrors) {
          setIsOpen(true);
        }
      }
      prevSaveAttempt.current = saveAttempt;
    }
  }, [saveAttempt, containsTracking, cronErrors]);

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
        <div style={{ marginTop: '1rem' }}>
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
  const shouldHaveBorder = isChatProviderSettings; // LlmProviderSettings is now handled by the wrapper

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
    // The title is now handled by the wrapper in CustomFieldTemplate
    title = null;
  } else if (isChatProviderSettings) {
    title = 'ChatProviderSettings';
  }

  // Hide the title for the inner oneOf selection, but show our custom one.
  // This is the definitive fix: explicitly check for the title we want to hide.
  // Also hide if title is empty or whitespace-only, or if it's "API Key Source" (shown as label instead)
  const isLlmModeTitle = props.title === 'Llm Mode';
  const isTitleEmpty = !title || (typeof title === 'string' && title.trim() === '');
  const isApiKeySourceTitle = props.title === 'API Key Source';
  const shouldShowTitle = !isLlmModeTitle && !isTitleEmpty && !isApiKeySourceTitle && ((title && shouldHaveBorder) || (props.title && !isLlmProviderSettings && props.title !== 'Respond Using Llm'));


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

// A field template that only renders the input, hiding label and description
// Used for inline compact rendering where labels are handled separately
export function InlineFieldTemplate(props) {
  const { children } = props;
  return children;
}

// An inline compact object template for array items like PeriodicGroupTrackingConfig
// Renders all fields on a single line with label:input pairs and tooltip descriptions
export function InlineObjectFieldTemplate(props) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
      {props.properties.map(element => {
        const schema = element.content.props.schema;
        const uiSchema = element.content.props.uiSchema || {};
        const description = schema?.description || '';
        // Use ui:title from uiSchema if available, otherwise fall back to schema title
        const label = uiSchema['ui:title'] || schema?.title || element.name;
        const isRequired = element.content.props.required;

        return (
          <div key={element.content.key} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <label
              htmlFor={element.content.props.idSchema.$id}
              title={description}
              style={{
                fontSize: '0.85rem',
                cursor: description ? 'help' : 'default',
                textDecoration: description ? 'underline dotted' : 'none',
                whiteSpace: 'nowrap'
              }}
            >
              {label}
            </label>
            {element.content}
          </div>
        );
      })}
    </div>
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
          <div key={element.key} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center' }}>
            <span style={{ marginRight: '0.5rem' }}>•</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
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

// Nested collapsible object template for sub-sections within main sections
export function NestedCollapsibleObjectFieldTemplate(props) {
  const [isOpen, setIsOpen] = useState(false);
  const { cronErrors, saveAttempt } = props.registry?.formContext || props.formContext || {};
  const prevSaveAttempt = useRef(saveAttempt);

  // Check if this section contains tracked_groups field (for periodic_group_tracking feature)
  const containsTrackedGroups = props.properties.some(p => p.name === 'tracked_groups');

  useEffect(() => {
    // Auto-expand when saveAttempt increments and there are cron errors
    if (saveAttempt !== prevSaveAttempt.current) {
      if (containsTrackedGroups && cronErrors && cronErrors.length > 0) {
        const hasErrors = cronErrors.some(e => e);
        if (hasErrors) {
          setIsOpen(true);
        }
      }
      prevSaveAttempt.current = saveAttempt;
    }
  }, [saveAttempt, containsTrackedGroups, cronErrors]);

  const containerStyle = {
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '0.75rem',
    margin: '0.5rem 0',
    backgroundColor: '#fafafa',
  };

  const titleStyle = {
    margin: 0,
    padding: 0,
    cursor: 'pointer',
    textAlign: 'left',
    fontSize: '0.95rem',
    fontWeight: 600,
  };

  return (
    <div style={containerStyle}>
      <h4 style={titleStyle} onClick={() => setIsOpen(!isOpen)}>
        {props.title} {isOpen ? '[-]' : '[+]'}
      </h4>
      {isOpen && (
        <div style={{ marginTop: '0.75rem' }}>
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
