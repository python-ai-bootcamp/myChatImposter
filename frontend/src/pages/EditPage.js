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
import { FloatingErrorBanner } from '../components/PageLayout';
import '../styles/DarkFormStyles.css';


function EditPage() {
  const { botId } = useParams();
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
  const [validationError, setValidationError] = useState(null);
  const [scrollToErrorTrigger, setScrollToErrorTrigger] = useState(0);

  const [userEnabled, setUserEnabled] = useState(location.state?.user_enabled !== undefined ? location.state.user_enabled : true);
  const isNew = location.state?.isNew;

  // Debounced validation (cron + backend API)
  useEffect(() => {
    const timer = setTimeout(async () => {
      // 1. Cron validation
      const tracking = formData?.features?.periodic_group_tracking?.tracked_groups;
      let newCronErrors = [];
      if (tracking && Array.isArray(tracking)) {
        for (let i = 0; i < tracking.length; i++) {
          const cron = tracking[i].cronTrackingSchedule;
          const validation = validateCronExpression(cron);
          if (!validation.valid) {
            newCronErrors[i] = validation.error;
          }
        }
      }
      if (JSON.stringify(newCronErrors) !== JSON.stringify(cronErrors)) {
        setCronErrors(newCronErrors);
      }

      // 2. Backend feature limit validation
      if (formData && botId) {
        try {
          const response = await fetch(`/api/external/ui/bots/${botId}/validate-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ features: formData.features || {} })
          });
          if (response.ok) {
            const result = await response.json();
            if (!result.valid) {
              setValidationError(result.error_message);
            } else {
              setValidationError(null);
            }
          }
        } catch (err) {
          console.warn('Validation API error:', err);
        }
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [formData, cronErrors, botId]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const schemaResponse = await fetch('/api/external/bots/schema');
        if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
        const schemaData = await schemaResponse.json();
        setSchema(schemaData);

        let initialFormData;
        if (isNew) {
          const defaultsResponse = await fetch('/api/external/bots/defaults');
          if (!defaultsResponse.ok) throw new Error('Failed to fetch configuration defaults.');
          initialFormData = await defaultsResponse.json();
          initialFormData.bot_id = botId;

          const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
          if (localTimezone && initialFormData.configurations?.user_details) {
            initialFormData.configurations.user_details.timezone = localTimezone;
          }



          // ... (inside EditPage component)

          try {
            const languagesResponse = await fetch('/api/external/resources/languages');
            if (languagesResponse.ok) {
              const languages = await languagesResponse.json();
              const browserLang = navigator.language || navigator.userLanguage;
              if (browserLang) {
                const baseLang = browserLang.split('-')[0].toLowerCase();
                const isSupported = languages.some(l => l.code === baseLang);
                if (isSupported && initialFormData.configurations?.user_details) {
                  initialFormData.configurations.user_details.language_code = baseLang;
                }
              }
            }
          } catch (langErr) {
            console.warn("Failed to auto-detect language:", langErr);
          }
        } else {
          const dataResponse = await fetch(`/api/external/bots/${botId}`);
          if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
          const data = await dataResponse.json();
          const originalData = Array.isArray(data) ? data[0] : data;

          if (originalData.configurations?.llm_configs) {
            ['high', 'low'].forEach(type => {
              const providerConfig = originalData.configurations.llm_configs[type]?.provider_config;
              if (providerConfig && !providerConfig.hasOwnProperty('api_key_source')) {
                if (providerConfig.api_key) {
                  providerConfig.api_key_source = 'explicit';
                } else {
                  providerConfig.api_key_source = 'environment';
                }
              }
            });
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
  }, [botId, isNew]);

  useEffect(() => {
    if (formData) {
      setJsonString(JSON.stringify(formData, null, 2));
    }
  }, [formData]);

  useEffect(() => {
    const fetchStatusAndGroups = async () => {
      try {
        const response = await fetch(`/api/external/bots/${botId}/status`);
        if (response.ok) {
          const data = await response.json();
          const status = data.status ? data.status.toLowerCase() : '';
          if (status === 'connected') {
            setIsLinked(true);
            try {
              const groupsRes = await fetch(`/api/external/bots/${botId}/groups`);
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
          setIsLinked(false);
          setAvailableGroups([]);
        }
      } catch (error) {
        setIsLinked(false);
        setAvailableGroups([]);
      }
    };
    fetchStatusAndGroups();
  }, [botId]);


  const handleScrollToError = () => {
    setScrollToErrorTrigger(prev => prev + 1);
    let attempts = 0;
    const maxAttempts = 10;
    const intervalTime = 100;
    const tryScroll = () => {
      const firstIndex = cronErrors.findIndex(e => e);
      if (firstIndex !== -1) {
        const elementId = `root_features_periodic_group_tracking_tracked_groups_${firstIndex}_cronTrackingSchedule`;
        const element = document.getElementById(elementId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          element.focus();
          return;
        }
      }
      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(tryScroll, intervalTime);
      }
    };
    setTimeout(tryScroll, 100);
  };

  const handleFormChange = (e) => {
    const newFormData = e.formData;
    try {
      // Logic for LLM Provider Config updates (api_key_source, reasoning_effort, seed) omitted for brevity but preserved in logic
      // Logic for LLM Provider Config updates (api_key_source, reasoning_effort, seed) for both High and Low
      ['high', 'low'].forEach(type => {
        const providerConfig = newFormData?.configurations?.llm_configs?.[type]?.provider_config;
        if (providerConfig) {
          if (providerConfig.api_key_source === 'environment') {
            providerConfig.api_key = null;
          } else if (providerConfig.api_key_source === 'explicit' && providerConfig.api_key === null) {
            providerConfig.api_key = "";
          }

          const oldProviderConfig = formData?.configurations?.llm_configs?.[type]?.provider_config;
          const newReasoningEffort = providerConfig.reasoning_effort;
          if (newReasoningEffort && !oldProviderConfig?.reasoning_effort) {
            if (newReasoningEffort !== 'minimal') providerConfig.reasoning_effort = 'minimal';
          }
        }
      });

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

      // 1. Cron Validation
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

      if (!isNew && currentData.bot_id !== botId) {
        throw new Error("The bot_id cannot be changed.");
      }

      const finalApiData = { ...currentData, bot_id: botId };
      const saveResponse = await fetch(`/api/external/bots/${botId}`, {
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

      if (mode === 'reload') {
        const reloadResponse = await fetch(`/api/external/bots/${botId}/actions/reload`, { method: 'POST' });
        if (!reloadResponse.ok) throw new Error('Failed to reload configuration.');
        navigate('/admin/dashboard');
      } else if (mode === 'link') {
        const createResponse = await fetch(`/api/external/bots/${botId}/actions/link`, { method: 'POST' });
        if (!createResponse.ok) throw new Error('Failed to start session.');
        navigate(`/admin/dashboard?auto_link=${botId}`);
      } else {
        navigate('/admin/dashboard');
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
    navigate('/admin/dashboard');
  };


  const pageBackground = { background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)', minHeight: '100vh', width: '100vw' };

  if (error) {
    return <div style={{ ...pageBackground, color: '#fca5a5', padding: '20px' }}>Error: {error}</div>;
  }

  if (!schema || !formData) {
    return <div style={{ ...pageBackground, color: '#e2e8f0', padding: '20px' }}>Loading form...</div>;
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
    CronInputWidget: CronPickerWidget,
    CronPickerWidget: CronPickerWidget,
    SystemPromptWidget: SystemPromptWidget,
    TimezoneSelectWidget: TimezoneSelectWidget,
    LanguageSelectWidget: LanguageSelectWidget
  };

  const uiSchema = {
    "ui:classNames": "form-container",
    "ui:title": " ",
    bot_id: { "ui:FieldTemplate": NullFieldTemplate },
    configurations: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "ui:title": "General Configurations",
      user_details: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "User Details",
        timezone: { "ui:widget": "TimezoneSelectWidget" },
        language_code: { "ui:widget": "LanguageSelectWidget" },
        activated: { "ui:FieldTemplate": InlineCheckboxFieldTemplate, "ui:title": "Auto Activate" }
      },
      chat_provider_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Chat Provider Config",
        provider_config: { "ui:title": " " }
      },
      queue_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Queue Config"
      },
      context_config: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Context Config"
      },
      llm_configs: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "LLM Configurations",
        high: {
          "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
          "ui:title": "High Performance Model",
          provider_name: { "ui:title": "Provider Name" },
          provider_config: {
            "ui:ObjectFieldTemplate": FlatProviderConfigTemplate,
            "ui:title": " ",
            api_key_source: { "ui:title": "API Key Source" },
            reasoning_effort: { "ui:title": "Reasoning Effort" },
            seed: { "ui:title": "Seed" }
          }
        },
        low: {
          "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
          "ui:title": "Low Cost Model",
          provider_name: { "ui:title": "Provider Name" },
          provider_config: {
            "ui:ObjectFieldTemplate": FlatProviderConfigTemplate,
            "ui:title": " ",
            api_key_source: { "ui:title": "API Key Source" },
            reasoning_effort: { "ui:title": "Reasoning Effort" },
            seed: { "ui:title": "Seed" }
          }
        }
      }
    },
    features: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "ui:title": "Feature Configurations",
      automatic_bot_reply: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Automatic Bot Reply",
        enabled: { "ui:FieldTemplate": InlineCheckboxFieldTemplate },
        respond_to_whitelist: { "ui:title": " " },
        respond_to_whitelist_group: { "ui:title": " " },
        chat_system_prompt: { "ui:widget": "textarea", "ui:options": { rows: 5 } }
      },
      periodic_group_tracking: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Periodic Group Tracking",
        enabled: { "ui:FieldTemplate": InlineCheckboxFieldTemplate },
        tracked_groups: {
          "ui:title": " ",
          "ui:ArrayFieldTemplate": GroupTrackingArrayTemplate,
          items: {
            "ui:ObjectFieldTemplate": InlineObjectFieldTemplate,
            "ui:order": ["displayName", "groupIdentifier", "cronTrackingSchedule"],
            displayName: { "ui:FieldTemplate": InlineFieldTemplate, "ui:title": "Name", "ui:widget": "GroupNameSelectorWidget" },
            groupIdentifier: { "ui:FieldTemplate": InlineFieldTemplate, "ui:title": "ID", "ui:widget": "ReadOnlyTextWidget" },
            cronTrackingSchedule: { "ui:FieldTemplate": InlineFieldTemplate, "ui:title": " ", "ui:widget": "CronPickerWidget", "ui:options": { width: "100%" }, "ui:placeholder": "0/15 * * * *" }
          }
        }
      },
      kid_phone_safety_tracking: {
        "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
        "ui:title": "Kid Phone Safety Tracking",
        enabled: { "ui:FieldTemplate": InlineCheckboxFieldTemplate }
      }
    }
  };

  return (
    <div className="profile-page">
      <style>{`
        .profile-page {
            height: calc(100vh - 60px);
            width: 100vw;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
            position: relative;
            overflow: hidden; /* Prevent external scroll */
            box-sizing: border-box;
        }

        .profile-container {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            padding: 2rem;
            padding-top: 1rem;
            border-radius: 1.5rem;
            width: 100%;
            max-width: 1800px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            z-index: 10;
            display: flex;
            flex-direction: column;
            height: 100%; /* Fill the page padding area */
            max-height: 100%;
            overflow: hidden; /* Prevent container scroll */
        }

        .profile-header {
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 1rem;
            flex-shrink: 0;
        }

        .profile-header h1 {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            margin-top: 0px;
            background: linear-gradient(to right, #c084fc, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Split Layout */
        .edit-content-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            flex: 1; /* Take remaining height */
            min-height: 0; /* Critical for nested scrolling */
            margin-bottom: 1rem;
            overflow: hidden;
        }

        .scroll-section {
            overflow-y: auto;
            height: 100%; /* Fill grid cell */
            padding-right: 10px;
            /* Custom scrollbar */
            scrollbar-width: thin;
            scrollbar-color: rgba(255,255,255,0.2) transparent;
        }
        .scroll-section::-webkit-scrollbar {
            width: 6px;
        }
        .scroll-section::-webkit-scrollbar-thumb {
            background-color: rgba(255,255,255,0.2);
            border-radius: 3px;
        }

        .json-editor-area {
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 0.75rem;
            color: #f8fafc;
            padding: 1rem;
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            resize: none;
            outline: none;
            box-sizing: border-box;
        }
        .json-editor-area:focus {
            border-color: #818cf8;
            box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2);
        }

        /* Background shapes */
        .shape {
            position: absolute;
            filter: blur(100px);
            z-index: 0;
            opacity: 0.4;
            pointer-events: none;
        }
        .shape-1 {
            top: -20%;
            left: -20%;
            width: 60vw;
            height: 60vw;
            background: radial-gradient(circle, #4f46e5 0%, transparent 70%);
        }
        .shape-2 {
            bottom: -20%;
            right: -20%;
            width: 50vw;
            height: 50vw;
            background: radial-gradient(circle, #ec4899 0%, transparent 70%);
        }

        /* Action Bar Styling */
        .action-bar {
            display: flex;
            gap: 1rem;
            justify-content: center;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 1rem;
            flex-shrink: 0;
        }

        .btn-glass {
            padding: 0.75rem 1.5rem;
            border-radius: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .btn-primary-glass {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.3);
        }
        .btn-primary-glass:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
        }

        .btn-success-glass {
            background: linear-gradient(135deg, #22c55e, #16a34a);
            color: white;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(34, 197, 94, 0.3);
        }
        .btn-success-glass:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(34, 197, 94, 0.4);
        }

        .btn-secondary-glass {
            background: rgba(30, 41, 59, 0.6);
            color: #e2e8f0;
        }
        .btn-secondary-glass:hover:not(:disabled) {
            background: rgba(30, 41, 59, 0.8);
        }

        .btn-glass:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
      `}</style>

      <div className="shape shape-1" />
      <div className="shape shape-2" />

      <FloatingErrorBanner isVisible={validationError || cronErrors.some(e => e)} darkMode={true}>
        <strong>⚠️ Cannot Save:</strong>
        {validationError ? (
          <span style={{ marginLeft: '5px' }}>{validationError}</span>
        ) : (
          <span
            onClick={handleScrollToError}
            style={{ marginLeft: '5px', textDecoration: 'underline', cursor: 'pointer', fontWeight: 'bold' }}
            title="Click to locate the error"
          >
            Invalid cron expression in tracked groups.
          </span>
        )}
      </FloatingErrorBanner>

      <div className="profile-container">
        <div className="profile-header">
          <h1>{isNew ? 'Add New Bot Configuration' : `Edit Bot ${botId}'s Configuration`}</h1>
        </div>

        <div className="edit-content-grid">
          {/* Left Column: Form */}
          <div className="scroll-section">
            <Form
              className="dark-form"
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
                saveAttempt,
                scrollToErrorTrigger,
                darkMode: true
              }}
            >
              <div />
            </Form>
          </div>

          {/* Right Column: JSON Editor */}
          <div className="scroll-section" style={{ display: 'flex', flexDirection: 'column' }}>
            <textarea
              aria-label="Live JSON Editor"
              className="json-editor-area"
              value={jsonString}
              onChange={handleJsonChange}
            />
            {jsonError && <p style={{ color: '#fca5a5', margin: '0.5rem 0 0 0', whiteSpace: 'pre-wrap' }}>{jsonError}</p>}
          </div>
        </div>

        {/* Action Bar */}
        <div className="action-bar">
          <button type="button" className="btn-glass btn-secondary-glass" onClick={handleCancel}>
            Cancel
          </button>

          <button
            type="button"
            className="btn-glass btn-success-glass"
            onClick={handleSaveAndLink}
            disabled={isSaving || isLinked || cronErrors.some(e => e) || validationError || !userEnabled}
            title={!userEnabled ? "Owner disabled due to quota depletion" : (validationError || (cronErrors.some(e => e) ? 'Fix cron errors first' : (!isLinked ? 'Save and link' : 'Only available when not connected')))}
          >
            {isSaving ? 'Saving...' : 'Save & Link'}
          </button>

          <button
            type="button"
            className="btn-glass btn-success-glass"
            onClick={handleSaveAndReload}
            disabled={isSaving || !isLinked || cronErrors.some(e => e) || validationError || !userEnabled}
            title={!userEnabled ? "Owner disabled due to quota depletion" : (validationError || (cronErrors.some(e => e) ? 'Fix cron errors first' : (isLinked ? 'Save and reload' : 'Only available when connected')))}
          >
            {isSaving ? 'Saving...' : 'Save & Reload'}
          </button>

          <button
            type="button"
            className="btn-glass btn-primary-glass"
            onClick={() => formRef.current.submit()}
            disabled={isSaving || cronErrors.some(e => e) || validationError}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default EditPage;
