import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import { CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget, CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate } from '../components/FormTemplates';
import { editPageLayout } from './EditPageLayout';

// Helper to transform schema based on the layout definition
const transformSchema = (originalSchema) => {
  const newSchema = JSON.parse(JSON.stringify(originalSchema));
  const newProperties = {};

  // Create new group schemas based on the layout config
  for (const groupName in editPageLayout.groups) {
    const groupConfig = editPageLayout.groups[groupName];
    const groupSchema = {
      type: 'object',
      title: groupConfig.title,
      properties: {},
      required: [],
    };

    // Move fields from the root schema into the new group schema
    for (const fieldName of groupConfig.fields) {
      if (newSchema.properties[fieldName]) {
        groupSchema.properties[fieldName] = newSchema.properties[fieldName];
        delete newSchema.properties[fieldName]; // Remove from root

        if (newSchema.required && newSchema.required.includes(fieldName)) {
          groupSchema.required.push(fieldName);
          newSchema.required = newSchema.required.filter(f => f !== fieldName);
        }
      }
    }

    newProperties[groupName] = groupSchema;
    if (groupSchema.required.length > 0) {
      if (!newSchema.required) newSchema.required = [];
      newSchema.required.push(groupName);
    }
  }

  // Combine the new group properties with the remaining root properties
  newSchema.properties = { ...newProperties, ...newSchema.properties };
  newSchema.title = ''; // Remove root title
  return newSchema;
};

// Helper to transform formData to match the new schema, based on the layout definition
const transformDataToUI = (data) => {
  if (!data) return data;
  const uiData = { ...data }; // Start with a copy of all original fields

  for (const groupName in editPageLayout.groups) {
    const groupConfig = editPageLayout.groups[groupName];
    const groupData = {}; // This will hold the fields for the new group

    for (const fieldName of groupConfig.fields) {
      // Check for the field on the original data object
      if (data[fieldName] !== undefined) {
        groupData[fieldName] = data[fieldName]; // Populate the group
        delete uiData[fieldName]; // Remove the original top-level field from our final UI data
      }
      // This logic is to ensure that a section is still rendered even if the data is missing.
      else if (fieldName === 'llm_provider_config') {
        groupData[fieldName] = null;
      }
    }
    // Now, assign the fully populated group to the UI data.
    // This avoids the previous bug where we would overwrite a field with an empty
    // object before we had a chance to process it (e.g. when groupName === fieldName).
    uiData[groupName] = groupData;
  }

  return uiData;
};

// A template that renders nothing, used to completely hide a field including its label and required asterisk
const NullFieldTemplate = () => null;

// Helper to transform formData back to the original format for saving
const transformDataToAPI = (uiData) => {
  if (!uiData) return uiData;
  const apiData = { ...uiData };

  for (const groupName in editPageLayout.groups) {
    const groupData = apiData[groupName];
    if (groupData) {
      // THE FIX IS HERE:
      // We must first copy the fields from the group, then delete the group container,
      // and only then assign the fields back. This avoids the bug where a field name
      // is the same as the group name, causing the data to be deleted.
      const fieldsToMove = { ...groupData };
      delete apiData[groupName];
      Object.assign(apiData, fieldsToMove);
    }
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
  const [isLinked, setIsLinked] = useState(false);

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

          // Perform on-the-fly migration for old configs that don't have api_key_source
          if (originalData.llm_provider_config && originalData.llm_provider_config.provider_config) {
            const providerConfig = originalData.llm_provider_config.provider_config;
            if (!providerConfig.hasOwnProperty('api_key_source')) {
              if (providerConfig.api_key) {
                providerConfig.api_key_source = 'explicit';
              } else {
                providerConfig.api_key_source = 'environment';
              }
            }
          }

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

  useEffect(() => {
    const fetchStatus = async () => {
        try {
            const response = await fetch(`/chatbot/${userId}/status`);
            if (response.ok) {
                const data = await response.json();
                if (data.status && data.status.toLowerCase() === 'connected') {
                    setIsLinked(true);
                }
            }
        } catch (error) {
            console.error("Failed to fetch user status:", error);
        }
    };
    fetchStatus();
  }, [userId]);

  const handleFormChange = (e) => {
    const newFormData = e.formData;
    try {
      // This handler is needed to work around a limitation in rjsf's handling of oneOf.
      // It doesn't automatically clear data from a previously selected oneOf branch.
      const providerConfig = newFormData?.llm_bot_config?.llm_provider_config?.provider_config;
      if (providerConfig) {
        if (providerConfig.api_key_source === 'environment') {
          // If the user selects 'environment', we must explicitly nullify the api_key.
          providerConfig.api_key = null;
        } else if (providerConfig.api_key_source === 'explicit' && providerConfig.api_key === null) {
          // If they switch to 'explicit' and the key is null, initialize it as an empty string
          // so the input box appears.
          providerConfig.api_key = "";
        }
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
      const apiDataFromUser = transformDataToAPI(formData);

      if (!isNew && apiDataFromUser.user_id !== userId) {
        throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
      }

      const finalApiData = { ...apiDataFromUser, user_id: userId };

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
        // First, save the configuration. We get the form data from the ref.
        const apiDataFromUser = transformDataToAPI(formRef.current.state.formData);

        if (!isNew && apiDataFromUser.user_id !== userId) {
            throw new Error("The user_id of an existing configuration cannot be changed. Please revert the user_id in the JSON editor to match the one in the URL.");
        }

        const finalApiData = { ...apiDataFromUser, user_id: userId };

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
        navigate(`/link/${userId}`);

    } catch (err) {
        setError(`Failed to save and reload: ${err.message}`);
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
        "ui:FieldTemplate": NullFieldTemplate
      },
      respond_to_whitelist: {
        "ui:title": " "
      }
    },
    chat_provider_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "chat_provider_config": {
        "ui:title": " "
      }
    },
    llm_bot_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      llm_provider_config: {
        "ui:title": "Llm Mode",
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
          }
        }
      }
    },
    queue_config: {
      "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
      "queue_config": {
        "ui:title": " "
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
          {isLinked && (
            <button type="button" onClick={handleSaveAndReload} disabled={isSaving} style={{ marginRight: '10px' }}>
              {isSaving ? 'Saving...' : 'Save & Reload'}
            </button>
          )}
          <button type="button" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      </div>
    </>
  );
}

export default EditPage;
