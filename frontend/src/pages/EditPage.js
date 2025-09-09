import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import { CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget, CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate } from '../components/FormTemplates';

// Helper to transform schema
const transformSchema = (originalSchema) => {
  const newSchema = JSON.parse(JSON.stringify(originalSchema));

  // --- Group GeneralConfig ---
  const generalConfigFields = ['user_id', 'respond_to_whitelist'];
  const generalConfigSchema = {
    type: 'object',
    title: 'GeneralConfig',
    properties: {},
    required: [],
  };
  for (const field of generalConfigFields) {
    if (newSchema.properties[field]) {
      generalConfigSchema.properties[field] = newSchema.properties[field];
      delete newSchema.properties[field];
      if (newSchema.required && newSchema.required.includes(field)) {
        generalConfigSchema.required.push(field);
        newSchema.required = newSchema.required.filter(f => f !== field);
      }
    }
  }

  // --- Group LlmBotConfig ---
  const llmBotConfigFields = ['llm_provider_config'];
  const llmBotConfigSchema = {
    type: 'object',
    title: 'LlmBotConfig',
    properties: {},
    required: [],
  };
  for (const field of llmBotConfigFields) {
    if (newSchema.properties[field]) {
      llmBotConfigSchema.properties[field] = newSchema.properties[field];
      delete newSchema.properties[field];
      if (newSchema.required && newSchema.required.includes(field)) {
        llmBotConfigSchema.required.push(field);
        newSchema.required = newSchema.required.filter(f => f !== field);
      }
    }
  }

  newSchema.properties = {
    general_config: generalConfigSchema,
    llm_bot_config: llmBotConfigSchema,
    ...newSchema.properties,
  };

  if (generalConfigSchema.required.length > 0) {
    if (!newSchema.required) newSchema.required = [];
    newSchema.required.push('general_config');
  }
  if (llmBotConfigSchema.required.length > 0) {
    if (!newSchema.required) newSchema.required = [];
    newSchema.required.push('llm_bot_config');
  }

  newSchema.title = ''; // Remove root title
  return newSchema;
};

// Helper to transform formData to match the new schema
const transformDataToUI = (data) => {
  if (!data) return data;
  const uiData = { ...data };

  uiData.general_config = {
    user_id: data.user_id,
    respond_to_whitelist: data.respond_to_whitelist,
  };
  delete uiData.user_id;
  delete uiData.respond_to_whitelist;

  uiData.llm_bot_config = {
    llm_provider_config: data.llm_provider_config,
  };
  delete uiData.llm_provider_config;

  return uiData;
};

// Helper to transform formData back to the original format for saving
const transformDataToAPI = (uiData) => {
  if (!uiData) return uiData;

  const { general_config, llm_bot_config, ...rest } = uiData;
  const apiData = { ...rest };

  if (general_config) {
    apiData.user_id = general_config.user_id;
    apiData.respond_to_whitelist = general_config.respond_to_whitelist;
  }

  if (llm_bot_config) {
    apiData.llm_provider_config = llm_bot_config.llm_provider_config;
  }

  return apiData;
};


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

  const isNew = location.state?.isNew;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const schemaResponse = await fetch('/api/configurations/schema');
        if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
        const schemaData = await schemaResponse.json();
        const transformedSchema = transformSchema(schemaData);
        setSchema(transformedSchema);

        let initialFormData;
        if (isNew) {
          const initialData = {
            user_id: userId,
            respond_to_whitelist: [],
          };
          initialFormData = transformDataToUI(initialData);
        } else {
          const dataResponse = await fetch(`/api/configurations/${userId}`);
          if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
          const data = await dataResponse.json();
          const originalData = Array.isArray(data) ? data[0] : data;
          initialFormData = transformDataToUI(originalData);
        }
        setFormData(initialFormData);
        setJsonString(JSON.stringify(transformDataToAPI(initialFormData), null, 2));

      } catch (err) {
        setError(err.message);
      }
    };

    fetchData();
  }, [userId, isNew]);

  useEffect(() => {
    if (formData) {
      setJsonString(JSON.stringify(transformDataToAPI(formData), null, 2));
    }
  }, [formData]);

  const handleFormChange = (e) => {
    const newFormData = e.formData;
    try {
      const providerConfig = newFormData?.llm_bot_config?.llm_provider_config?.provider_config;
      if (providerConfig) {
        // Case 1: Switching from "From Environment" (null) to "User Specific Key" (string).
        // The new value becomes `undefined`. We fix this by setting it to an empty string.
        if (typeof providerConfig.api_key === 'undefined') {
          providerConfig.api_key = "";
        }
        // Case 2: Switching from "User Specific Key" (string) to "From Environment" (null).
        // The new value becomes an empty string `""`. We fix this by setting it to `null`.
        // This also means that a user manually clearing the text box will switch the dropdown, which is acceptable UX.
        else if (providerConfig.api_key === "") {
          providerConfig.api_key = null;
        }
      }
    } catch (error) {
      // It's possible the form data structure is not what we expect during some transitions.
      // We can ignore errors here as this is just a stabilization helper.
    }
    setFormData(newFormData);
  };

  const handleJsonChange = (event) => {
    const newJsonString = event.target.value;
    setJsonString(newJsonString);
    try {
      const parsedData = JSON.parse(newJsonString);
      const uiData = transformDataToUI(parsedData);
      setFormData(uiData);
      setJsonError(null);
    } catch (err) {
      setJsonError('Invalid JSON: ' + err.message);
    }
  };

  const handleSave = async ({ formData }) => {
    setIsSaving(true);
    setError(null);
    try {
      // formData reflects the latest state from the form or the JSON editor.
      const apiDataFromUser = transformDataToAPI(formData);

      // For existing configs, check if the user tried to change the ID in the JSON editor.
      if (!isNew && apiDataFromUser.user_id !== userId) {
        throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
      }

      // Ensure the data we send to the API has the correct, authoritative user_id from the URL.
      const finalApiData = { ...apiDataFromUser, user_id: userId };

      // The PUT request should always go to the URL's userId endpoint.
      const response = await fetch(`/api/configurations/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify([finalApiData]), // Send the cleaned data
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
    CheckboxWidget: CustomCheckboxWidget
  };

  const uiSchema = {
    "ui:classNames": "form-container",
    general_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      user_id: {
        "ui:widget": "hidden"
      }
    },
    chat_provider_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate
    },
    llm_bot_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "ui:title": "LlmBotConfig",
    },
    queue_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate
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
              <div style={{...innerPanelStyle, overflowY: 'auto'}}>
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
                >
                  <div />
                </Form>
              </div>

              <div style={{ ...innerPanelStyle, display: 'flex', flexDirection: 'column' }}>
                <h3>Live JSON Editor</h3>
                <textarea
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
          <button type="button" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      </div>
    </>
  );
}

export default EditPage;
