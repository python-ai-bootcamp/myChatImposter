import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { validateConfiguration } from '../configModels';

function EditPage() {
  const { filename } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [content, setContent] = useState('');
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const isNew = location.state?.isNew;

  useEffect(() => {
    const fetchFileContent = async () => {
      try {
        const response = await fetch(`/api/configurations/${filename}`);
        if (!response.ok) {
          throw new Error('Failed to fetch file content.');
        }
        const data = await response.json();
        setContent(JSON.stringify(data, null, 2));
      } catch (err) {
        setError(err.message);
      }
    };

    if (isNew) {
      const defaultConfig = {
        user_id: filename.replace('.json', ''),
        respond_to_whitelist: [],
        chat_provider_config: {
          provider_name: 'dummy',
          provider_config: {
            allow_group_messages: false,
            process_offline_messages: false,
          }
        },
        queue_config: {
          max_messages: 10,
          max_characters: 1000,
          max_days: 1,
          max_characters_single_message: 300,
        },
        llm_provider_config: null,
      };
      setContent(JSON.stringify(defaultConfig, null, 2));
    } else {
      fetchFileContent();
    }
  }, [filename, isNew]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const parsedContent = JSON.parse(content);

      // Frontend validation
      const validationResult = validateConfiguration(parsedContent);
      if (!validationResult.isValid) {
        const errorMessages = validationResult.errors.map(e => `Validation error at ${e.path}: ${e.message}`).join('\n');
        throw new Error(errorMessages);
      }

      const response = await fetch(`/api/configurations/${filename}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(parsedContent),
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
      if (err instanceof SyntaxError) {
        setError(`Invalid JSON syntax: ${err.message}`);
      } else {
        setError(`Failed to save: ${err.message}`);
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/');
  };

  if (error && !isSaving) {
    // For new files, we don't want to show a "failed to fetch" error initially
    if (isNew && error && error.includes('Failed to fetch file content')) {
      // clear error
        setError(null);
    } else {
      return <div>Error: {error}</div>;
    }
  }

  return (
    <div>
      <h2>{isNew ? 'Add' : 'Edit'}: {filename}</h2>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows="20"
        cols="80"
        style={{ whiteSpace: 'pre', overflowWrap: 'normal', overflowX: 'scroll', width: '100%' }}
      />
      <div>
        <button onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save'}
        </button>
        <button onClick={handleCancel}>Cancel</button>
      </div>
      {error && <p style={{ color: 'red', whiteSpace: 'pre-wrap' }}>{error}</p>}
    </div>
  );
}

export default EditPage;
