import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import FlexibleForm from '../components/FlexibleForm/Form';
import { editPageLayout } from './EditPageLayout';
import Ajv from 'ajv';

const ajv = new Ajv({ allErrors: true, verbose: true, strict: false });

function EditPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [schema, setSchema] = useState(null);
  const [formData, setFormData] = useState(null);
  const [jsonString, setJsonString] = useState('');
  const [jsonError, setJsonError] = useState(null);
  const [formErrors, setFormErrors] = useState([]);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const isNew = location.state?.isNew;

  const validate = (data, currentSchema) => {
    if (!currentSchema) return [];
    const validate = ajv.compile(currentSchema);
    const valid = validate(data);
    if (!valid) {
      return validate.errors;
    }
    return [];
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const schemaResponse = await fetch('/api/configurations/schema');
        if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
        const schemaData = await schemaResponse.json();
        setSchema(schemaData);

        let initialFormData;
        if (isNew) {
          initialFormData = {
            user_id: userId,
            respond_to_whitelist: [],
          };
        } else {
          const dataResponse = await fetch(`/api/configurations/${userId}`);
          if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
          const data = await dataResponse.json();
          initialFormData = Array.isArray(data) ? data[0] : data;

          if (initialFormData.llm_provider_config && initialFormData.llm_provider_config.provider_config) {
            const providerConfig = initialFormData.llm_provider_config.provider_config;
            if (!providerConfig.hasOwnProperty('api_key_source')) {
              if (providerConfig.api_key) {
                providerConfig.api_key_source = 'explicit';
              } else {
                providerConfig.api_key_source = 'environment';
              }
            }
          }
        }
        setFormData(initialFormData);
        setJsonString(JSON.stringify(initialFormData, null, 2));
        setFormErrors(validate(initialFormData, schemaData));
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

  const handleFormChange = (newFormData) => {
    try {
      const providerConfig = newFormData?.llm_provider_config?.provider_config;
      if (providerConfig) {
        if (providerConfig.api_key_source === 'environment') {
          providerConfig.api_key = null;
        } else if (providerConfig.api_key_source === 'explicit' && providerConfig.api_key === null) {
          providerConfig.api_key = "";
        }
      }
    } catch (error) {
        // ignore
    }
    setFormData(newFormData);
    const errors = validate(newFormData, schema);
    setFormErrors(errors);
  };

  const handleJsonChange = (event) => {
    const newJsonString = event.target.value;
    setJsonString(newJsonString);
    try {
      const parsedData = JSON.parse(newJsonString);
      setFormData(parsedData);
      setJsonError(null);
      const errors = validate(parsedData, schema);
      setFormErrors(errors);
    } catch (err) {
      setJsonError('Invalid JSON: ' + err.message);
      setFormErrors([]);
    }
  };

  const handleSave = async () => {
    if (jsonError) {
      setError("Cannot save, the JSON is invalid.");
      return;
    }
    if (formErrors.length > 0) {
      setError("Cannot save, form has validation errors.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const apiDataFromUser = formData;

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

  const handleCancel = () => {
    navigate('/');
  };

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!schema || !formData) {
    return <div>Loading form...</div>;
  }

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
                <FlexibleForm
                  layout={editPageLayout}
                  schema={schema}
                  formData={formData}
                  onFormChange={handleFormChange}
                  errors={formErrors}
                />
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
          <button type="button" onClick={handleSave} disabled={isSaving || !!jsonError || formErrors.length > 0} style={{ marginRight: '10px' }}>
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
