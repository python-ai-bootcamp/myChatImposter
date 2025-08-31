import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

function EditPage() {
  const { filename } = useParams();
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

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

    fetchFileContent();
  }, [filename]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const parsedContent = JSON.parse(content);

      // Add validation to ensure it's a JSON object
      if (typeof parsedContent !== 'object' || parsedContent === null || Array.isArray(parsedContent)) {
        throw new Error('Configuration must be a valid JSON object (e.g., { "key": "value" }).');
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
        throw new Error(errorBody.detail || 'Failed to save file.');
      }

      navigate('/');
    } catch (err) {
      // Differentiate between JSON parsing errors and fetch errors
      const errorMessage = err.message.includes('JSON')
        ? `Invalid JSON: ${err.message}`
        : `Failed to save: ${err.message}`;
      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/');
  };

  if (error && !isSaving) {
    return <div>Error: {error}</div>;
  }

  return (
    <div>
      <h2>Edit: {filename}</h2>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows="20"
        cols="80"
        style={{ width: '100%' }}
      />
      <div>
        <button onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save'}
        </button>
        <button onClick={handleCancel}>Cancel</button>
      </div>
      {error && isSaving && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}

export default EditPage;
