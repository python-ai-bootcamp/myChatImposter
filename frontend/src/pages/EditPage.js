import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import {
  CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget,
  CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate, InlineObjectFieldTemplate,
  InlineFieldTemplate, NarrowTextWidget, SizedTextWidget,
  NestedCollapsibleObjectFieldTemplate, SystemPromptWidget, InlineCheckboxFieldTemplate,
  FlatProviderConfigTemplate, TimezoneSelectWidget, LanguageSelectWidget
} from '../components/FormTemplates';
import { GroupTrackingArrayTemplate } from '../components/templates/GroupTrackingArrayTemplate';
import { NullFieldTemplate } from '../components/templates/NullFieldTemplate';
import { GroupNameSelectorWidget } from '../components/widgets/GroupNameSelectorWidget';
import { ReadOnlyTextWidget } from '../components/widgets/ReadOnlyTextWidget';
import { validateCronExpression } from '../utils/validation';
import CronPickerWidget from '../components/CronPickerWidget';




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
        const schemaResponse = await fetch('/api/external/users/schema');
        if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
        const schemaData = await schemaResponse.json();
        setSchema(schemaData);

        let initialFormData;
        if (isNew) {
          // Fetch dynamic defaults from backend (Single Source of Truth)
          const defaultsResponse = await fetch('/api/external/users/defaults');
          if (!defaultsResponse.ok) throw new Error('Failed to fetch configuration defaults.');
          initialFormData = await defaultsResponse.json();

          // Override with current context
          initialFormData.user_id = userId;

          // Use browser's detected timezone instead of backend default (usually UTC)
          const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
          if (localTimezone && initialFormData.configurations?.user_details) {
            initialFormData.configurations.user_details.timezone = localTimezone;
          }
        } else {
          const dataResponse = await fetch(`/api/external/users/${userId}`);
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
        const response = await fetch(`/api/external/users/${userId}/status`);
        if (response.ok) {
          const data = await response.json();
          const status = data.status ? data.status.toLowerCase() : '';
          // isConnected is true only when the user is actively connected
          // This enables "Save & Reload". Otherwise, "Save & Link" is available.
          if (status === 'connected') {
            setIsLinked(true);
            // Fetch available groups when connected
            try {
              console.log("Fetching groups for connected user...");
              const groupsRes = await fetch(`/api/external/users/${userId}/groups`);
              if (groupsRes.ok) {
                const groupsData = await groupsRes.json();
                console.log("Fetched groups:", groupsData.groups?.length);
                setAvailableGroups(groupsData.groups || []);
              } else {
                console.error("Failed to fetch groups:", groupsRes.status);
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

        // Logic for Seed auto-selection (similar to reasoning_effort)
        const oldSeed = oldProviderConfig?.seed;
        const newSeed = providerConfig.seed;

        // DEBUG: Log seed transition
        // console.log('Seed transition:', { oldSeed, newSeed, typeOfNew: typeof newSeed });

        // When switching anyOf from Undefined to Defined, rjsf sets seed to undefined
        // We need to detect this and set a default value of 0.
        // However, when switching FROM Defined TO Undefined, rjsf ALSO sets seed to undefined.
        // We must distinguish the two cases using oldSeed.

        // Case 1: Switching from Undefined to Defined
        // oldSeed is null/undefined, newSeed is undefined/empty -> Set default 0
        if ((oldSeed === null || oldSeed === undefined) &&
          (newSeed === undefined || newSeed === "")) {
          console.log('Switching to Defined -> Setting seed to 0');
          providerConfig.seed = 0;
        }

        // Case 2: Switching from Defined to Undefined
        // oldSeed is a number, newSeed is undefined -> Do nothing (let it be undefined)

        // Case 3: Invalid number input while Defined
        // newSeed is NaN -> Reset to 0
        if (typeof newSeed === 'number' && isNaN(newSeed)) {
          console.log('Invalid number -> Resetting seed to 0');
          providerConfig.seed = 0;
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

  const saveConfiguration = async (mode, submitData = formData) => {
    setIsSaving(true);
    setError(null);
    try {
      const currentData = submitData;

      // 1. Validate Cron Expressions
      setCronErrors([]);
      let hasCronErrors = false;
      const newCronErrors = [];
      const tracking = currentData?.features?.periodic_group_tracking?.tracked_groups;

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
        // Scroll to error
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

      // 2. Validate User ID
      if (!isNew && currentData.user_id !== userId) {
        throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
      }

      // 3. Save Configuration (PUT)
      const finalApiData = { ...currentData, user_id: userId };
      const saveResponse = await fetch(`/api/external/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalApiData),
      });

      if (!saveResponse.ok) {
        const errorBody = await saveResponse.json();
        const detail = typeof errorBody.detail === 'object' && errorBody.detail !== null
          ? JSON.stringify(errorBody.detail, null, 2)
          : errorBody.detail;
        throw new Error(detail || 'Failed to save configuration.');
      }

      // 4. Handle Post-Save Actions
      if (mode === 'reload') {
        const reloadResponse = await fetch(`/api/external/users/${userId}/actions/reload`, {
          method: 'POST',
        });
        if (!reloadResponse.ok) {
          const errorBody = await reloadResponse.json();
          throw new Error(errorBody.detail || 'Failed to reload configuration.');
        }
        navigate('/');
      } else if (mode === 'link') {
        const createResponse = await fetch(`/api/external/users/${userId}/actions/link`, {
          method: 'POST',
        });
        if (!createResponse.ok) {
          const errorBody = await createResponse.json();
          throw new Error(errorBody.detail || `Failed to start session (HTTP ${createResponse.status})`);
        }
        navigate(`/?auto_link=${userId}`);
      } else {
        // mode === 'save'
        navigate('/');
      }

    } catch (err) {
      setError(`Failed during ${mode}: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSave = ({ formData: submittedData }) => saveConfiguration('save', submittedData);
  const handleSaveAndReload = () => saveConfiguration('reload');
  const handleSaveAndLink = () => saveConfiguration('link');

  const handleCancel = () => {
    navigate('/');
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
    CronInputWidget: CronPickerWidget, // Map old name to new widget, or just use new name
    CronPickerWidget: CronPickerWidget,
    SystemPromptWidget: SystemPromptWidget,
    TimezoneSelectWidget: TimezoneSelectWidget,
    LanguageSelectWidget: LanguageSelectWidget
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
      user_details: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "User Details",
        timezone: {
          "ui:widget": "TimezoneSelectWidget"
        },
        language_code: {
          "ui:widget": "LanguageSelectWidget"
        }
      },
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
        provider_name: {
          "ui:title": "Provider Name"
        },
        provider_config: {
          "ui:ObjectFieldTemplate": FlatProviderConfigTemplate,
          "ui:title": " ",
          api_key_source: {
            "ui:title": "API Key Source"
          },
          reasoning_effort: {
            "ui:title": "Reasoning Effort"
          },
          seed: {
            "ui:title": "Seed"
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
        },
        chat_system_prompt: {
          "ui:widget": "textarea",
          "ui:options": {
            rows: 5
          }
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
              "ui:title": "ID",
              "ui:widget": "ReadOnlyTextWidget"
            },
            cronTrackingSchedule: {
              "ui:FieldTemplate": InlineFieldTemplate,
              "ui:title": " ",
              "ui:widget": "CronPickerWidget",
              "ui:options": { width: "100%" },
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
