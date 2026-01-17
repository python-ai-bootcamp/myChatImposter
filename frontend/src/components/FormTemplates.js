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

// Common IANA timezones with friendly display names
const COMMON_TIMEZONES = [
  'UTC',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Moscow',
  'Asia/Jerusalem',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Bangkok',
  'Asia/Singapore',
  'Asia/Hong_Kong',
  'Asia/Tokyo',
  'Australia/Sydney',
  'Pacific/Auckland',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
  'Africa/Cairo',
  'Africa/Johannesburg'
];

// Get UTC offset string for a timezone (e.g., "+02:00", "-05:00")
function getTimezoneOffset(timezone) {
  try {
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      timeZoneName: 'shortOffset'
    });
    const parts = formatter.formatToParts(now);
    const offsetPart = parts.find(p => p.type === 'timeZoneName');
    if (offsetPart) {
      // Convert "GMT+2" to "+02:00" format
      const value = offsetPart.value;
      if (value === 'GMT') return '+00:00';
      const match = value.match(/GMT([+-])(\d+)(?::(\d+))?/);
      if (match) {
        const sign = match[1];
        const hours = match[2].padStart(2, '0');
        const mins = match[3] || '00';
        return `${sign}${hours}:${mins}`;
      }
      return value.replace('GMT', '');
    }
  } catch (e) {
    return '';
  }
  return '';
}

// Filterable timezone dropdown widget
export function TimezoneSelectWidget(props) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [filter, setFilter] = React.useState('');
  const containerRef = React.useRef(null);

  // Build timezone options with offsets
  const timezoneOptions = React.useMemo(() => {
    return COMMON_TIMEZONES.map(tz => ({
      value: tz,
      label: tz.replace(/_/g, ' '),
      offset: getTimezoneOffset(tz)
    })).sort((a, b) => {
      // Sort by offset, then alphabetically
      const offsetA = a.offset || '+00:00';
      const offsetB = b.offset || '+00:00';
      if (offsetA !== offsetB) return offsetA.localeCompare(offsetB);
      return a.label.localeCompare(b.label);
    });
  }, []);

  // Filter options based on input
  const filteredOptions = React.useMemo(() => {
    if (!filter) return timezoneOptions;
    const lowerFilter = filter.toLowerCase();
    return timezoneOptions.filter(opt =>
      opt.label.toLowerCase().includes(lowerFilter) ||
      opt.value.toLowerCase().includes(lowerFilter) ||
      opt.offset.includes(lowerFilter)
    );
  }, [filter, timezoneOptions]);

  // Get display text for current value
  const currentOption = timezoneOptions.find(opt => opt.value === props.value);
  const displayText = currentOption
    ? `${currentOption.label} (${currentOption.offset})`
    : props.value || 'Select timezone...';

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (value) => {
    props.onChange(value);
    setIsOpen(false);
    setFilter('');
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block', width: '250px' }}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '4px 8px',
          border: '1px solid #ccc',
          borderRadius: '3px',
          cursor: 'pointer',
          backgroundColor: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayText}
        </span>
        <span style={{ marginLeft: '8px' }}>{isOpen ? '▲' : '▼'}</span>
      </div>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          border: '1px solid #ccc',
          borderRadius: '3px',
          backgroundColor: '#fff',
          zIndex: 1000,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          maxHeight: '250px',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <input
            type="text"
            placeholder="Filter..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            style={{
              padding: '6px 8px',
              border: 'none',
              borderBottom: '1px solid #eee',
              outline: 'none',
              width: '100%',
              boxSizing: 'border-box'
            }}
            autoFocus
          />
          <div style={{ overflowY: 'auto', maxHeight: '200px' }}>
            {filteredOptions.map(opt => (
              <div
                key={opt.value}
                onClick={() => handleSelect(opt.value)}
                style={{
                  padding: '6px 8px',
                  cursor: 'pointer',
                  backgroundColor: opt.value === props.value ? '#e6f7ff' : 'transparent',
                  display: 'flex',
                  justifyContent: 'space-between'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                onMouseLeave={(e) => e.target.style.backgroundColor = opt.value === props.value ? '#e6f7ff' : 'transparent'}
              >
                <span>{opt.label}</span>
                <span style={{ color: '#888', fontSize: '0.9em' }}>{opt.offset}</span>
              </div>
            ))}
            {filteredOptions.length === 0 && (
              <div style={{ padding: '8px', color: '#888', textAlign: 'center' }}>No matches</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Common ISO 639-1 language codes with display names
const COMMON_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'he', name: 'Hebrew (עברית)' },
  { code: 'ar', name: 'Arabic (العربية)' },
  { code: 'es', name: 'Spanish (Español)' },
  { code: 'fr', name: 'French (Français)' },
  { code: 'de', name: 'German (Deutsch)' },
  { code: 'ru', name: 'Russian (Русский)' },
  { code: 'zh', name: 'Chinese (中文)' },
  { code: 'ja', name: 'Japanese (日本語)' },
  { code: 'pt', name: 'Portuguese (Português)' },
  { code: 'it', name: 'Italian (Italiano)' },
  { code: 'ko', name: 'Korean (한국어)' },
  { code: 'nl', name: 'Dutch (Nederlands)' },
  { code: 'pl', name: 'Polish (Polski)' },
  { code: 'tr', name: 'Turkish (Türkçe)' },
  { code: 'hi', name: 'Hindi (हिन्दी)' },
  { code: 'th', name: 'Thai (ไทย)' },
  { code: 'vi', name: 'Vietnamese (Tiếng Việt)' },
  { code: 'uk', name: 'Ukrainian (Українська)' },
  { code: 'sv', name: 'Swedish (Svenska)' }
];

// Filterable language dropdown widget
export function LanguageSelectWidget(props) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [filter, setFilter] = React.useState('');
  const containerRef = React.useRef(null);

  // Build language options
  const languageOptions = React.useMemo(() => {
    return COMMON_LANGUAGES.map(lang => ({
      value: lang.code,
      label: lang.name,
      code: lang.code.toUpperCase()
    })).sort((a, b) => a.label.localeCompare(b.label));
  }, []);

  // Filter options based on input
  const filteredOptions = React.useMemo(() => {
    if (!filter) return languageOptions;
    const lowerFilter = filter.toLowerCase();
    return languageOptions.filter(opt =>
      opt.label.toLowerCase().includes(lowerFilter) ||
      opt.value.toLowerCase().includes(lowerFilter)
    );
  }, [filter, languageOptions]);

  // Get display text for current value
  const currentOption = languageOptions.find(opt => opt.value === props.value);
  const displayText = currentOption
    ? `${currentOption.label} (${currentOption.code})`
    : props.value || 'Select language...';

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (value) => {
    props.onChange(value);
    setIsOpen(false);
    setFilter('');
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block', width: '250px' }}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '4px 8px',
          border: '1px solid #ccc',
          borderRadius: '3px',
          cursor: 'pointer',
          backgroundColor: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayText}
        </span>
        <span style={{ marginLeft: '8px' }}>{isOpen ? '▲' : '▼'}</span>
      </div>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          border: '1px solid #ccc',
          borderRadius: '3px',
          backgroundColor: '#fff',
          zIndex: 1000,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          maxHeight: '250px',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <input
            type="text"
            placeholder="Filter..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            style={{
              padding: '6px 8px',
              border: 'none',
              borderBottom: '1px solid #eee',
              outline: 'none',
              width: '100%',
              boxSizing: 'border-box'
            }}
            autoFocus
          />
          <div style={{ overflowY: 'auto', maxHeight: '200px' }}>
            {filteredOptions.map(opt => (
              <div
                key={opt.value}
                onClick={() => handleSelect(opt.value)}
                style={{
                  padding: '6px 8px',
                  cursor: 'pointer',
                  backgroundColor: opt.value === props.value ? '#e6f7ff' : 'transparent',
                  display: 'flex',
                  justifyContent: 'space-between'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                onMouseLeave={(e) => e.target.style.backgroundColor = opt.value === props.value ? '#e6f7ff' : 'transparent'}
              >
                <span>{opt.label}</span>
                <span style={{ color: '#888', fontSize: '0.9em' }}>{opt.code}</span>
              </div>
            ))}
            {filteredOptions.length === 0 && (
              <div style={{ padding: '8px', color: '#888', textAlign: 'center' }}>No matches</div>
            )}
          </div>
        </div>
      )}
    </div>
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

// A flat object template that renders children without the panel-body wrapper
// Used for llm_provider_config.provider_config to flatten the oneOf dropdown alignment
export function FlatProviderConfigTemplate(props) {
  // Separate boolean fields from other fields - booleans render outside the table
  const tableFields = props.properties.filter(element => {
    const schema = element.content?.props?.schema;
    return schema?.type !== 'boolean';
  });
  const booleanFields = props.properties.filter(element => {
    const schema = element.content?.props?.schema;
    return schema?.type === 'boolean';
  });

  return (
    <>
      <div style={{ display: 'table', width: '100%', borderCollapse: 'collapse' }}>
        {tableFields.map(element => (
          <React.Fragment key={element.content.key}>
            {element.content}
          </React.Fragment>
        ))}
      </div>
      {booleanFields.map(element => (
        <React.Fragment key={element.content.key}>
          {element.content}
        </React.Fragment>
      ))}
    </>
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

  // Render API Key Source dropdown with proper table-row layout matching other fields
  // This needs to output the same structure as the standard CustomFieldTemplate for consistency
  if (id && id.includes('provider_config__oneof_select')) {
    return (
      <div className={classNames} style={{ display: 'table-row', textAlign: 'left' }}>
        <label style={{ display: 'table-cell', whiteSpace: 'nowrap', verticalAlign: 'top', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0 }}>
          API Key Source
        </label>
        <div style={{ boxSizing: 'border-box', textAlign: 'left', display: 'table-cell', width: '100%' }}>
          {children}
        </div>
      </div>
    );
  }

  // Flatten the provider_config field structure - render children directly
  if (id && (id.endsWith('chat_provider_config_provider_config') || id.endsWith('llm_provider_config_provider_config'))) {
    return children;
  }

  // Indent API Key field to align with Reasoning Effort dropdown
  // Render with empty first cell so it appears in the right column
  if (id && id.endsWith('provider_config_api_key')) {
    return (
      <div style={{ display: 'table-row' }}>
        <div style={{ display: 'table-cell' }}></div>
        <div style={{ display: 'table-cell', textAlign: 'left', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ whiteSpace: 'nowrap' }}>{label}</span>
            {children}
          </div>
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

  // Special handling for boolean fields - pure flex layout to avoid table-cell centering issues
  if (schema.type === 'boolean') {
    return (
      <div className={classNames} style={{
        display: 'flex',
        flexDirection: 'row',
        justifyContent: 'flex-start',
        alignItems: 'center',
        gap: '1rem',
        marginTop: '0.5rem',
        marginBottom: '0.5rem',
        textAlign: 'left'
      }}>
        <span style={{ whiteSpace: 'nowrap', minWidth: '110px' }}>
          {label}
        </span>
        <input
          type="checkbox"
          id={id}
          checked={typeof props.formData === 'undefined' ? false : props.formData}
          onChange={(e) => props.onChange(e.target.checked)}
          style={{ margin: 0, marginLeft: '18px' }}
        />
      </div>
    );
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
