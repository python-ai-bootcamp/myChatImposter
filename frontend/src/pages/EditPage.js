import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import { CustomFieldTemplate, CustomObjectFieldTemplate } from '../components/FormTemplates';

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
        setSchema(schemaData);

        // Fetch existing data or set up new data
        if (isNew) {
          // For a new file, we can start with an empty object or some defaults.
          // RJSF will use the schema's defaults if available.
          setFormData({
            user_id: filename.replace('.json', ''),
            // Set other defaults if necessary, but RJSF handles schema defaults
          });
        } else {
          const dataResponse = await fetch(`/api/configurations/${filename}`);
          if (!dataResponse.ok) throw new Error('Failed to fetch file content.');
          const data = await dataResponse.json();
          // The config might be in an array
          setFormData(Array.isArray(data) ? data[0] : data);
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
      // The react-jsonschema-form component validates the data against the schema internally.
      // The onSubmit handler is only called if the data is valid.
      const response = await fetch(`/api/configurations/${filename}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        // The backend endpoint expects a list for a new file,
        // and a single object for an existing one. We will send a list for new files.
        body: JSON.stringify([formData]),
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
    ObjectFieldTemplate: CustomObjectFieldTemplate
  };

  const uiSchema = {
    llm_provider_config: {
      provider_config: {
        api_key: {
          "ui:widget": "password"
        }
      }
    }
  };

  return (
    <div>
      <h2>{isNew ? 'Add' : 'Edit'}: {filename}</h2>
      <Form
        schema={schema}
        uiSchema={uiSchema}
        formData={formData}
        validator={validator}
        onSubmit={handleSave}
        onError={(errors) => console.log('Form validation errors:', errors)}
        disabled={isSaving}
        templates={templates}
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
      {error && <p style={{ color: 'red', whiteSpace: 'pre-wrap', marginTop: '10px' }}>{error}</p>}
    </div>
  );
}

export default EditPage;
