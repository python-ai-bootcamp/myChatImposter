import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import { CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget, CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate } from '../components/FormTemplates';

// Helper to transform schema
const transformSchema = (originalSchema) => {
  const newSchema = JSON.parse(JSON.stringify(originalSchema));
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

  newSchema.properties = {
    general_config: generalConfigSchema,
    ...newSchema.properties,
  };

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
  return uiData;
};

// Helper to transform formData back to the original format for saving
const transformDataToAPI = (uiData) => {
  if (!uiData) return uiData;
  const apiData = { ...uiData };
  if (uiData.general_config) {
    apiData.user_id = uiData.general_config.user_id;
    apiData.respond_to_whitelist = uiData.general_config.respond_to_whitelist;
  }
  delete apiData.general_config;
  return apiData;
};


function EditPage() {
  const { filename } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

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
    llm_provider_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "ui:title": "LlmBotConfig",
      "ui:classNames": "llm-provider-selector",
      provider_config: {
        api_key: {
          "ui:widget": "password"
        }
      }
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
    <div style={{ maxWidth: '1800px', margin: '0 auto', padding: '20px' }}>
      <div style={panelStyle}>
        <h2>{isNew ? 'Add' : 'Edit'}: {filename}</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '1rem' }}>
          {/* Left Panel: Form Editor */}
          <div style={panelStyle}>
            <Form
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
              <div>
                <button type="submit" disabled={isSaving}>
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
                <button type="button" onClick={handleCancel} style={{ marginLeft: '10px' }}>
                  Cancel
                </button>
              </div>
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
  );
}

export default EditPage;
