import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import { CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget, CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate } from '../components/FormTemplates';

// Helper to transform schema
const transformSchema = (originalSchema) => {
  const newSchema = JSON.parse(JSON.stringify(originalSchema));

  // Group GeneralConfig
  const generalConfigFields = ['user_id', 'respond_to_whitelist'];
  const generalConfigSchema = {
    type: 'object',
    title: 'GeneralConfig',
    properties: {},
  };
  for (const field of generalConfigFields) {
    if (newSchema.properties[field]) {
      generalConfigSchema.properties[field] = newSchema.properties[field];
      delete newSchema.properties[field];
    }
  }

  // Group LlmBotConfig
  const llmBotConfigFields = ['llm_provider_config'];
  const llmBotConfigSchema = {
    type: 'object',
    title: 'LlmBotConfig',
    properties: {},
  };
  for (const field of llmBotConfigFields) {
    if (newSchema.properties[field]) {
      llmBotConfigSchema.properties[field] = newSchema.properties[field];
      delete newSchema.properties[field];
    }
  }

  newSchema.properties = {
    general_config: generalConfigSchema,
    llm_bot_config: llmBotConfigSchema,
    ...newSchema.properties,
  };

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

  // Destructure to separate the nested UI objects from the rest of the data
  const { general_config, llm_bot_config, ...rest } = uiData;
  const apiData = { ...rest }; // Start with the flat properties

  // Flatten the nested properties back to the top level
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
  const { filename } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const formRef = useRef(null);

  const [schema, setSchema] = useState(null);
  const [formData, setFormData] = useState(null);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const isNew = location.state?.isNew;

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch schema
        const schemaResponse = await fetch('/api/configurations/schema');
        if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
        const schemaData = await schemaResponse.json();
        const transformedSchema = transformSchema(schemaData);
        setSchema(transformedSchema);

        // Fetch existing data or set up new data
        if (isNew) {
          const initialData = {
            user_id: filename.replace('.json', ''),
            respond_to_whitelist: [],
          };
          setFormData(transformDataToUI(initialData));
        } else {
          const dataResponse = await fetch(`/api/configurations/${filename}`);
          if (!dataResponse.ok) throw new Error('Failed to fetch file content.');
          const data = await dataResponse.json();
          const originalData = Array.isArray(data) ? data[0] : data;
          setFormData(transformDataToUI(originalData));
        }
      } catch (err) {
        setError(err.message);
      }
    };

    fetchData();
  }, [filename, isNew]);

  const handleSave = async ({ formData }) => {
    setIsSaving(true);
    setError(null);
    try {
      const apiData = transformDataToAPI(formData);
      const response = await fetch(`/api/configurations/${filename}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify([apiData]),
      });

      if (!response.ok) {
        const errorBody = await response.json();
        const detail = typeof errorBody.detail === 'object' && errorBody.detail !== null
            ? JSON.stringify(errorBody.detail, null, 2)
            : errorBody.detail;
        throw new Error(detail || 'Failed to save file.');
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
    backgroundColor: '#f9f9f9',
    boxSizing: 'border-box'
  };

  return (
    <>
      <div style={{ padding: '20px', paddingBottom: '80px' }}> {/* paddingBottom to make space for footer */}
        <div style={{ maxWidth: '1800px', margin: '0 auto' }}>
          <div style={panelStyle}>
            <h2>{isNew ? 'Add' : 'Edit'}: {filename}</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '1rem' }}>
              {/* Left Panel: Form Editor */}
              <div style={panelStyle}>
                <Form
                  ref={formRef}
                  schema={schema}
                  uiSchema={uiSchema}
                  formData={formData}
                  validator={validator}
                  onSubmit={handleSave}
                  onChange={(e) => setFormData(e.formData)}
                  onError={(errors) => console.log('Form validation errors:', errors)}
                  disabled={isSaving}
                  templates={templates}
                  widgets={widgets}
                >
                  {/* Buttons are now in the footer */}
                  <div />
                </Form>
              </div>

              {/* Right Panel: Live JSON Output */}
              <div style={panelStyle}>
                <h3>Live JSON Output</h3>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', textAlign: 'left' }}>
                  <code>
                    {JSON.stringify(formData, null, 2)}
                  </code>
                </pre>
              </div>
            </div>
          </div>
          {error && <p style={{ color: 'red', whiteSpace: 'pre-wrap', marginTop: '10px' }}>{error}</p>}
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
        <button type="button" onClick={() => formRef.current.submit()} disabled={isSaving} style={{ marginRight: '10px' }}>
          {isSaving ? 'Saving...' : 'Save'}
        </button>
        <button type="button" onClick={handleCancel}>
          Cancel
        </button>
      </div>
    </>
  );
}

export default EditPage;
