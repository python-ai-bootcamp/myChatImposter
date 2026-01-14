import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import { CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget, CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate, InlineObjectFieldTemplate, InlineFieldTemplate, NarrowTextWidget, SizedTextWidget, NestedCollapsibleObjectFieldTemplate, SystemPromptWidget, InlineCheckboxFieldTemplate } from '../components/FormTemplates';

// Stable widget definitions - defined outside component to prevent re-creation on re-render
const ReadOnlyTextWidget = (props) => {
  return (
    <input
      type="text"
      value={props.value || ''}
      disabled
      style={{ width: '180px', backgroundColor: '#f5f5f5', color: '#666' }}
      title="Auto-filled from group selection"
    />
  );
};

// Group Name Selector Widget - uses formContext to access state
const GroupNameSelectorWidget = (props) => {
  const { availableGroups, isLinked, formData, setFormData } = props.formContext || {};
  const [inputValue, setInputValue] = React.useState(props.value || '');
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const isFocusedRef = React.useRef(false);

  // Only sync from props when not focused (external changes like JSON editor)
  React.useEffect(() => {
    if (!isFocusedRef.current) {
      setInputValue(props.value || '');
    }
  }, [props.value]);

  const groups = availableGroups || [];
  const filteredGroups = groups.filter(g =>
    (g.subject || '').toLowerCase().includes((inputValue || '').toLowerCase())
  );

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    setIsMenuOpen(true);
    props.onChange(e.target.value);
  };

  const handleFocus = () => {
    isFocusedRef.current = true;
    setIsMenuOpen(true);
  };

  const handleBlur = () => {
    isFocusedRef.current = false;
    setTimeout(() => setIsMenuOpen(false), 200);
  };

  const handleSelect = (group) => {
    setInputValue(group.subject);
    setIsMenuOpen(false);

    // Extract the array index from the widget's id
    // New path: root_features_periodic_group_tracking_tracked_groups_0_displayName
    const idMatch = props.id.match(/tracked_groups_(\d+)_displayName$/);
    if (idMatch && formData && setFormData) {
      const idx = parseInt(idMatch[1], 10);
      const currentData = JSON.parse(JSON.stringify(formData));
      if (currentData?.features?.periodic_group_tracking?.tracked_groups?.[idx]) {
        currentData.features.periodic_group_tracking.tracked_groups[idx].groupIdentifier = group.id;
        currentData.features.periodic_group_tracking.tracked_groups[idx].displayName = group.subject;
        setFormData(currentData);
      }
    }
  };

  if (!isLinked) {
    return (
      <input
        type="text"
        value={props.value || '(connect to select)'}
        disabled
        style={{ width: '150px', backgroundColor: '#f0f0f0' }}
        title="Adding or changing group details is prohibited for disconnected users"
      />
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <input
        type="text"
        placeholder="Type group name..."
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        style={{ width: '150px', padding: '4px' }}
      />
      {isMenuOpen && filteredGroups.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          width: '300px',
          maxHeight: '200px',
          overflowY: 'auto',
          border: '1px solid #ccc',
          backgroundColor: '#fff',
          zIndex: 1000,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
        }}>
          {filteredGroups.map(g => (
            <div
              key={g.id}
              onMouseDown={() => handleSelect(g)}
              style={{ padding: '8px', cursor: 'pointer', borderBottom: '1px solid #eee' }}
            >
              <strong>{g.subject}</strong><br />
              <small style={{ color: '#666' }}>{g.id}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Custom array template for tracked_groups - disables Add when not connected
// Uses formContext to access isLinked state
const GroupTrackingArrayTemplate = (props) => {
  const { isLinked } = props.formContext || {};

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

      {/* Add button - only enabled when connected */}
      <button
        type="button"
        onClick={props.onAddClick}
        disabled={!isLinked}
        style={{
          ...btnStyle,
          padding: '0.3rem 0.6rem',
          marginTop: '0.5rem',
          opacity: isLinked ? 1 : 0.5
        }}
        title={isLinked ? 'Add new group' : 'Adding or changing group details is prohibited for disconnected users'}
      >
        + Add
      </button>
    </div>
  );
};

// Cron input widget that shows validation errors inline
const CronInputWidget = (props) => {
  const { cronErrors } = props.formContext || {};

  // Extract index from ID: root_features_periodic_group_tracking_tracked_groups_0_cronTrackingSchedule
  const idMatch = props.id.match(/tracked_groups_(\d+)_cronTrackingSchedule$/);
  const index = idMatch ? parseInt(idMatch[1], 10) : -1;
  const error = cronErrors && cronErrors[index];

  const width = props.options?.width || '120px';
  const style = {
    width,
    // Only apply error styles, let defaults handle the rest
    ...(error ? {
      border: '2px solid red',
      outline: 'none',
      boxShadow: '0 0 3px red'
    } : {})
  };

  return (
    <input
      type="text"
      id={props.id}
      value={props.value || ''}
      required={props.required}
      onChange={(event) => props.onChange(event.target.value)}
      style={style}
      placeholder={props.placeholder || "0/15 * * * *"}
      title={error ? `Error: ${error}` : "Cron expression: minute hour day month weekday"}
    />
  );
};

// A template that renders nothing, used to completely hide a field including its label and required asterisk
const NullFieldTemplate = () => null;


function EditPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const formRef = useRef(null);

  const [schema, setSchema] = useState(null);
  const [formData, setFormData] = useState(null);
  const [jsonString, setJsonString] = useState('');
  const [jsonError, setJsonError] = useState(null);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLinked, setIsLinked] = useState(false);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [cronErrors, setCronErrors] = useState([]);
  const [saveAttempt, setSaveAttempt] = useState(0);

  const isNew = location.state?.isNew;

  // Scheduled check for cron errors (polling/debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      const tracking = formData?.features?.periodic_group_tracking?.tracked_groups;
      if (tracking && Array.isArray(tracking)) {
        const newCronErrors = [];

        for (let i = 0; i < tracking.length; i++) {
          const cron = tracking[i].cronTrackingSchedule;
          const validation = validateCronExpression(cron);
          if (!validation.valid) {
            newCronErrors[i] = validation.error;
          }
        }

        // Compare with current errors to avoid unnecessary re-renders
        if (JSON.stringify(newCronErrors) !== JSON.stringify(cronErrors)) {
          setCronErrors(newCronErrors);
        }
      } else {
        if (cronErrors.length > 0) setCronErrors([]);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [formData, cronErrors]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const schemaResponse = await fetch('/api/configurations/schema');
        if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
        const schemaData = await schemaResponse.json();
        setSchema(schemaData);

        let initialFormData;
        if (isNew) {
          // Initialize with the new structure
          initialFormData = {
            user_id: userId,
            configurations: {
              chat_provider_config: {
                provider_name: 'whatsapp_baileys',
                provider_config: {
                  allow_group_messages: false,
                  process_offline_messages: false
                }
              },
              queue_config: {
                max_messages: 10,
                max_characters: 1000,
                max_days: 1,
                max_characters_single_message: 300
              },
              context_config: {
                max_messages: 10,
                max_characters: 1000,
                max_days: 1,
                max_characters_single_message: 300,
                shared_context: true
              }
            },
            features: {
              automatic_bot_reply: {
                enabled: false,
                respond_to_whitelist: [],
                respond_to_whitelist_group: []
              },
              periodic_group_tracking: {
                enabled: false,
                tracked_groups: []
              },
              kid_phone_safety_tracking: {
                enabled: false
              }
            }
          };
        } else {
          const dataResponse = await fetch(`/api/configurations/${userId}`);
          if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
          const data = await dataResponse.json();
          const originalData = Array.isArray(data) ? data[0] : data;

          // Perform on-the-fly migration for old configs that don't have api_key_source
          if (originalData.configurations?.llm_provider_config?.provider_config) {
            const providerConfig = originalData.configurations.llm_provider_config.provider_config;
            if (!providerConfig.hasOwnProperty('api_key_source')) {
              if (providerConfig.api_key) {
                providerConfig.api_key_source = 'explicit';
              } else {
                providerConfig.api_key_source = 'environment';
              }
            }
          }

          initialFormData = originalData;
        }
        setFormData(initialFormData);
        setJsonString(JSON.stringify(initialFormData, null, 2));

      } catch (err) {
        setError(err.message);
      }
    };

    fetchData();
  }, [userId, isNew]);

  useEffect(() => {
    if (formData) {
      setJsonString(JSON.stringify(formData, null, 2));
    }
  }, [formData]);

  useEffect(() => {
    const fetchStatusAndGroups = async () => {
      try {
        const response = await fetch(`/chatbot/${userId}/status`);
        if (response.ok) {
          const data = await response.json();
          const status = data.status ? data.status.toLowerCase() : '';
          // isConnected is true only when the user is actively connected
          // This enables "Save & Reload". Otherwise, "Save & Link" is available.
          if (status === 'connected') {
            setIsLinked(true);
            // Fetch available groups when connected
            try {
              const groupsRes = await fetch(`/chatbot/${userId}/groups`);
              if (groupsRes.ok) {
                const groupsData = await groupsRes.json();
                setAvailableGroups(groupsData.groups || []);
              }
            } catch (groupsError) {
              console.warn("Could not fetch groups:", groupsError);
            }
          } else {
            setIsLinked(false);
            setAvailableGroups([]);
          }
        } else {
          // If the status endpoint returns 404, it means the session is not active.
          setIsLinked(false);
          setAvailableGroups([]);
        }
      } catch (error) {
        console.error("Failed to fetch user status:", error);
        setIsLinked(false);
        setAvailableGroups([]);
      }
    };
    fetchStatusAndGroups();
  }, [userId]);

  const handleFormChange = (e) => {
    const newFormData = e.formData;
    try {
      // This handler is needed to work around a limitation in rjsf's handling of oneOf.
      // It doesn't automatically clear data from a previously selected oneOf branch.
      const providerConfig = newFormData?.configurations?.llm_provider_config?.provider_config;
      if (providerConfig) {
        if (providerConfig.api_key_source === 'environment') {
          // If the user selects 'environment', we must explicitly nullify the api_key.
          providerConfig.api_key = null;
        } else if (providerConfig.api_key_source === 'explicit' && providerConfig.api_key === null) {
          // If they switch to 'explicit' and the key is null, initialize it as an empty string
          // so the input box appears.
          providerConfig.api_key = "";
        }

        // Logic for Reasoning Effort auto-selection
        const oldProviderConfig = formData?.configurations?.llm_provider_config?.provider_config;
        const oldReasoningEffort = oldProviderConfig?.reasoning_effort;
        const newReasoningEffort = providerConfig.reasoning_effort;

        // If reasoning_effort was previously null/undefined (Undefined) and is now set (Defined),
        // and it's not 'minimal', set it to 'minimal'.
        // This handles the transition from "Undefined" to "Defined".
        // Note: rjsf might default it to the first enum value (e.g. 'low').
        if (newReasoningEffort && !oldReasoningEffort) {
          if (newReasoningEffort !== 'minimal') {
            providerConfig.reasoning_effort = 'minimal';
          }
        }
      }

      // Auto-populate displayName when groupIdentifier is selected
      const tracking = newFormData?.features?.periodic_group_tracking?.tracked_groups;
      if (tracking && Array.isArray(tracking) && availableGroups.length > 0) {
        tracking.forEach(item => {
          if (item.groupIdentifier) {
            const group = availableGroups.find(g => g.id === item.groupIdentifier);
            if (group && item.displayName !== group.subject) {
              item.displayName = group.subject;
            }
          }
        });
      }
    } catch (error) {
      // ignore
    }
    setFormData(newFormData);
  };

  const handleJsonChange = (event) => {
    const newJsonString = event.target.value;
    setJsonString(newJsonString);
    try {
      const parsedData = JSON.parse(newJsonString);
      setFormData(parsedData);
      setJsonError(null);
    } catch (err) {
      setJsonError('Invalid JSON: ' + err.message);
    }
  };

  const handleSave = async ({ formData }) => {
    setIsSaving(true);
    setError(null);
    try {
      // Validate cron expressions before saving
      setCronErrors([]); // Reset errors
      let hasCronErrors = false;
      const newCronErrors = [];
      const tracking = formData?.features?.periodic_group_tracking?.tracked_groups;
      if (tracking && Array.isArray(tracking)) {
        for (let i = 0; i < tracking.length; i++) {
          const cron = tracking[i].cronTrackingSchedule;
          const validation = validateCronExpression(cron);
          if (!validation.valid) {
            newCronErrors[i] = validation.error;
            hasCronErrors = true;
          }
        }
      }

      if (hasCronErrors) {
        setCronErrors(newCronErrors);
        setSaveAttempt(prev => prev + 1);
        setIsSaving(false);
        // Scroll to the first error
        setTimeout(() => {
          const firstIndex = newCronErrors.findIndex(e => e);
          if (firstIndex !== -1) {
            const elementId = `root_features_periodic_group_tracking_tracked_groups_${firstIndex}_cronTrackingSchedule`;
            const element = document.getElementById(elementId);
            if (element) {
              element.scrollIntoView({ behavior: 'smooth', block: 'center' });
              element.focus();
            }
          }
        }, 100);
        return;
      }

      if (!isNew && formData.user_id !== userId) {
        throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
      }

      const finalApiData = { ...formData, user_id: userId };

      const response = await fetch(`/api/configurations/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify([finalApiData]),
      });

      if (!response.ok) {
        const errorBody = await response.json();
        const detail = typeof errorBody.detail === 'object' && errorBody.detail !== null
          ? JSON.stringify(errorBody.detail, null, 2)
          : errorBody.detail;
        throw new Error(detail || 'Failed to save configuration.');
      }

      navigate('/');
    } catch (err) {
      setError(`Failed to save: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAndReload = async () => {
    setIsSaving(true);
    setError(null);
    try {
      // Validate cron expressions before saving
      setCronErrors([]); // Reset errors
      let hasCronErrors = false;
      const newCronErrors = [];
      const currentFormData = formData;
      const tracking = currentFormData?.features?.periodic_group_tracking?.tracked_groups;
      if (tracking && Array.isArray(tracking)) {
        for (let i = 0; i < tracking.length; i++) {
          const cron = tracking[i].cronTrackingSchedule;
          const validation = validateCronExpression(cron);
          if (!validation.valid) {
            newCronErrors[i] = validation.error;
            hasCronErrors = true;
          }
        }
      }

      if (hasCronErrors) {
        setCronErrors(newCronErrors);
        setSaveAttempt(prev => prev + 1);
        setIsSaving(false);
        // Scroll to the first error
        setTimeout(() => {
          const firstIndex = newCronErrors.findIndex(e => e);
          if (firstIndex !== -1) {
            const elementId = `root_features_periodic_group_tracking_tracked_groups_${firstIndex}_cronTrackingSchedule`;
            const element = document.getElementById(elementId);
            if (element) {
              element.scrollIntoView({ behavior: 'smooth', block: 'center' });
              element.focus();
            }
          }
        }, 100);
        return;
      }

      // First, save the configuration. We get the form data from the ref.
      if (!isNew && formData.user_id !== userId) {
        throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
      }

      const finalApiData = { ...formData, user_id: userId };

      const saveResponse = await fetch(`/api/configurations/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([finalApiData]),
      });

      if (!saveResponse.ok) {
        const errorBody = await saveResponse.json();
        throw new Error(errorBody.detail || 'Failed to save configuration.');
      }

      // If save is successful, then reload
      const reloadResponse = await fetch(`/chatbot/${userId}/reload`, {
        method: 'POST',
      });

      if (!reloadResponse.ok) {
        const errorBody = await reloadResponse.json();
        throw new Error(errorBody.detail || 'Failed to reload configuration.');
      }

      // If both are successful, navigate to the link page
      navigate('/');

    } catch (err) {
      setError(`Failed to save and reload: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAndLink = async () => {
    setIsSaving(true);
    setError(null);
    try {
      // Validate cron expressions before saving
      setCronErrors([]); // Reset errors
      let hasCronErrors = false;
      const newCronErrors = [];
      const currentFormData = formData;
      const tracking = currentFormData?.features?.periodic_group_tracking?.tracked_groups;
      if (tracking && Array.isArray(tracking)) {
        for (let i = 0; i < tracking.length; i++) {
          const cron = tracking[i].cronTrackingSchedule;
          const validation = validateCronExpression(cron);
          if (!validation.valid) {
            newCronErrors[i] = validation.error;
            hasCronErrors = true;
          }
        }
      }

      if (hasCronErrors) {
        setCronErrors(newCronErrors);
        setSaveAttempt(prev => prev + 1);
        setIsSaving(false);
        // Scroll to the first error
        setTimeout(() => {
          const firstIndex = newCronErrors.findIndex(e => e);
          if (firstIndex !== -1) {
            const elementId = `root_features_periodic_group_tracking_tracked_groups_${firstIndex}_cronTrackingSchedule`;
            const element = document.getElementById(elementId);
            if (element) {
              element.scrollIntoView({ behavior: 'smooth', block: 'center' });
              element.focus();
            }
          }
        }, 100);
        return;
      }

      // Save the configuration first
      if (!isNew && formData.user_id !== userId) {
        throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
      }

      const finalApiData = { ...formData, user_id: userId };

      const saveResponse = await fetch(`/api/configurations/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([finalApiData]),
      });

      if (!saveResponse.ok) {
        const errorBody = await saveResponse.json();
        throw new Error(errorBody.detail || 'Failed to save configuration.');
      }

      // Start the session by calling PUT /chatbot with the config payload
      const createResponse = await fetch('/chatbot', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalApiData),
      });

      if (!createResponse.ok) {
        const errorBody = await createResponse.json();
        throw new Error(errorBody.detail || `Failed to start session (HTTP ${createResponse.status})`);
      }

      // Navigate to the link page to show linking status
      navigate('/');

    } catch (err) {
      setError(`Failed to save and link: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/');
  };

  // Cron validation helper
  const validateCronExpression = (cron) => {
    if (!cron) return { valid: false, error: 'Required' };
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) {
      return { valid: false, error: 'Must have 5 parts (min hour day month weekday)' };
    }
    const validChars = /^[0-9*/,\-]+$/;
    if (!parts.every(p => validChars.test(p))) {
      return { valid: false, error: 'Invalid characters. Allowed: 0-9 * / , -' };
    }
    return { valid: true, error: null };
  };

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!schema || !formData) {
    return <div>Loading form...</div>;
  }

  const templates = {
    FieldTemplate: CustomFieldTemplate,
    ObjectFieldTemplate: CustomObjectFieldTemplate,
    ArrayFieldTemplate: CustomArrayFieldTemplate
  };

  const widgets = {
    CheckboxWidget: CustomCheckboxWidget,
    NarrowTextWidget: NarrowTextWidget,
    SizedTextWidget: SizedTextWidget,
    GroupNameSelectorWidget: GroupNameSelectorWidget,
    ReadOnlyTextWidget: ReadOnlyTextWidget,
    CronInputWidget: CronInputWidget,
    SystemPromptWidget: SystemPromptWidget
  };

  const uiSchema = {
    "ui:classNames": "form-container",
    "ui:title": " ",
    user_id: {
      "ui:FieldTemplate": NullFieldTemplate
    },
    // General Configurations section
    configurations: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "ui:title": "General Configurations",
      chat_provider_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Chat Provider Config",
        provider_config: {
          "ui:title": " "
        }
      },
      queue_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Queue Config"
      },
      context_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Context Config"
      },
      llm_provider_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "LLM Provider Config",
        provider_config: {
          "ui:title": "API Key Source",
          "ui:options": {
            "box": "LlmProviderSettings"
          },
          api_key_source: {
            "ui:options": {
              "hidden": true
            },
            "ui:enumNames": [
              "API Key From Environment",
              "API Key From User Input"
            ]
          },
          reasoning_effort: {
            "ui:title": "Reasoning Effort",
            "ui:widget": "select",
            "ui:options": {
              "optionTitles": ["Defined", "Undefined"]
            }
          },
          system: {
            "ui:title": "System Prompt",
            "ui:widget": "SystemPromptWidget"
          }
        }
      }
    },
    // Feature Configurations section
    features: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "ui:title": "Feature Configurations",
      automatic_bot_reply: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Automatic Bot Reply",
        enabled: {
          "ui:FieldTemplate": InlineCheckboxFieldTemplate
        },
        respond_to_whitelist: {
          "ui:title": " "
        },
        respond_to_whitelist_group: {
          "ui:title": " "
        }
      },
      periodic_group_tracking: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Periodic Group Tracking",
        enabled: {
          "ui:FieldTemplate": InlineCheckboxFieldTemplate
        },
        tracked_groups: {
          "ui:title": " ",
          "ui:ArrayFieldTemplate": GroupTrackingArrayTemplate,
          items: {
            "ui:ObjectFieldTemplate": InlineObjectFieldTemplate,
            "ui:order": ["displayName", "groupIdentifier", "cronTrackingSchedule"],
            displayName: {
              "ui:FieldTemplate": InlineFieldTemplate,
              "ui:title": "Name",
              "ui:widget": "GroupNameSelectorWidget"
            },
            groupIdentifier: {
              "ui:FieldTemplate": InlineFieldTemplate,
              "ui:title": "Identifier",
              "ui:widget": "ReadOnlyTextWidget"
            },
            cronTrackingSchedule: {
              "ui:FieldTemplate": InlineFieldTemplate,
              "ui:title": "Schedule",
              "ui:widget": "CronInputWidget",
              "ui:options": { width: "90px" },
              "ui:placeholder": "0/15 * * * *"
            }
          }
        }
      },
      kid_phone_safety_tracking: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Kid Phone Safety Tracking",
        enabled: {
          "ui:FieldTemplate": InlineCheckboxFieldTemplate
        }
      }
    }
  };

  const panelStyle = {
    border: '1px solid #ccc',
    borderRadius: '4px',
    padding: '1rem',
    backgroundColor: '#fff',
    boxSizing: 'border-box'
  };

  const innerPanelStyle = {
    ...panelStyle,
    backgroundColor: '#f9f9f9',
  };

  return (
    <>
      <div style={{ padding: '20px', paddingBottom: '80px' }}>
        <div style={{ maxWidth: '1800px', margin: '0 auto' }}>
          <div style={panelStyle}>
            <h2>{isNew ? 'Add New Configuration' : `Edit Configuration`}: {userId}</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '1rem', minHeight: '75vh' }}>
              <div style={{ ...innerPanelStyle, overflowY: 'auto' }}>
                <Form
                  ref={formRef}
                  schema={schema}
                  uiSchema={uiSchema}
                  formData={formData}
                  validator={validator}
                  onSubmit={handleSave}
                  onChange={handleFormChange}
                  onError={(errors) => console.log('Form validation errors:', errors)}
                  disabled={isSaving}
                  templates={templates}
                  widgets={widgets}
                  formContext={{
                    availableGroups,
                    isLinked,
                    formData,
                    setFormData,
                    cronErrors,
                    saveAttempt
                  }}
                >
                  <div />
                </Form>
              </div>

              <div style={{ ...innerPanelStyle, display: 'flex', flexDirection: 'column' }}>
                <h3>Live JSON Editor</h3>
                <textarea
                  aria-label="Live JSON Editor"
                  style={{ flex: 1, fontFamily: 'monospace', fontSize: '0.9rem', border: jsonError ? '1px solid red' : '1px solid #ccc', resize: 'vertical', padding: '0.5rem' }}
                  value={jsonString}
                  onChange={handleJsonChange}
                />
                {jsonError && <p style={{ color: 'red', margin: '0.5rem 0 0 0', whiteSpace: 'pre-wrap' }}>{jsonError}</p>}
              </div>
            </div>
          </div>
        </div>
      </div>
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '1rem',
        backgroundColor: '#f0f0f0',
        borderTop: '1px solid #ccc',
        textAlign: 'center'
      }}>
        {error && <p style={{ color: 'red', whiteSpace: 'pre-wrap', marginBottom: '1rem' }}>{error}</p>}
        <div>
          <button type="button" onClick={() => formRef.current.submit()} disabled={isSaving} style={{ marginRight: '10px' }}>
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            onClick={handleSaveAndReload}
            disabled={isSaving || !isLinked}
            style={{ marginRight: '10px', opacity: isLinked ? 1 : 0.5 }}
            title={isLinked ? 'Save and reload the configuration for the connected user' : 'Only available when user is connected'}
          >
            {isSaving ? 'Saving...' : 'Save & Reload'}
          </button>
          <button
            type="button"
            onClick={handleSaveAndLink}
            disabled={isSaving || isLinked}
            style={{ marginRight: '10px', opacity: !isLinked ? 1 : 0.5 }}
            title={!isLinked ? 'Save and start the linking flow' : 'Only available when user is not connected'}
          >
            {isSaving ? 'Saving...' : 'Save & Link'}
          </button>
          <button type="button" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      </div>
    </>
  );
}

export default EditPage;
