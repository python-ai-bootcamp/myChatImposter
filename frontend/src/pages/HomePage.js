import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function HomePage() {
  const [configs, setConfigs] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchStatuses = async () => {
    try {
      // Don't clear old error, so it persists until next success
      const response = await fetch('/api/configurations/status');
      if (!response.ok) {
        // Don't throw, just show an error and let polling continue
        setError('Failed to fetch configuration statuses.');
        return;
      }
      const data = await response.json();
      setConfigs(data.configurations || []);
      setError(null); // Clear error on success
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchStatuses();
    const interval = setInterval(fetchStatuses, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const handleLink = async () => {
    if (!selectedFile) return;

    setIsLinking(true);
    setError(null);

    try {
      // 1. Fetch the configuration content
      const configResponse = await fetch(`/api/configurations/${selectedFile}`);
      if (!configResponse.ok) {
        throw new Error('Failed to fetch configuration file.');
      }
      const configData = await configResponse.json();

      // 2. Create the user instance
      const createResponse = await fetch('/chatbot', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configData),
      });

      if (!createResponse.ok) {
        const errorBody = await createResponse.json();
        throw new Error(errorBody.detail || `Failed to create session (HTTP ${createResponse.status})`);
      }

      const createData = await createResponse.json();

      if (createData.failed && createData.failed.length > 0) {
        throw new Error(`Failed to create instance: ${createData.failed[0].error}`);
      }

      const userId = createData.successful[0].user_id;

      // 3. Navigate to the link page
      navigate(`/link/${userId}`);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLinking(false);
    }
  };

  const handleEdit = () => {
    if (selectedFile) {
      navigate(`/edit/${selectedFile}`);
    }
  };

  const handleAdd = async () => {
    const filename = prompt('Enter new filename (e.g., "my-config.json"):');
    if (!filename) {
      return; // User cancelled
    }

    if (!filename.endsWith('.json')) {
      alert('Filename must end with .json');
      return;
    }

    if (configs.some(c => c.filename === filename)) {
      alert(`File "${filename}" already exists.`);
      return;
    }

    try {
      const defaultConfig = {
        user_id: filename.replace('.json', ''),
        respond_to_whitelist: [],
        chat_provider_config: {
          provider_name: 'dummy',
          allow_group_messages: false,
          process_offline_messages: false,
        },
        queue_config: {
          max_messages: 10,
          max_characters: 1000,
          max_days: 1,
          max_characters_single_message: 300,
        },
        llm_provider_config: null,
      };

      const response = await fetch(`/api/configurations/${filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(defaultConfig), // Create with a default object
      });

      if (!response.ok) {
        const errorBody = await response.json();
        throw new Error(errorBody.detail || 'Failed to create file.');
      }

      await fetchStatuses(); // Refresh the file list immediately
    } catch (err) {
      setError(`Failed to create file: ${err.message}`);
    }
  };

  const handleDelete = async () => {
    if (!selectedFile) {
      return;
    }

    if (window.confirm(`Are you sure you want to delete "${selectedFile}"?`)) {
      try {
        const response = await fetch(`/api/configurations/${selectedFile}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          const errorBody = await response.json();
          throw new Error(errorBody.detail || 'Failed to delete file.');
        }

        setSelectedFile(null); // Deselect the file
        await fetchStatuses();   // Refresh the list
      } catch (err) {
        setError(`Failed to delete file: ${err.message}`);
      }
    }
  };

  const handleUnlink = async () => {
    const config = configs.find(c => c.filename === selectedFile);
    if (!config || !config.user_id) return;

    if (window.confirm(`Are you sure you want to unlink user "${config.user_id}"?`)) {
      try {
        const response = await fetch(`/chatbot/${config.user_id}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          const errorBody = await response.json();
          throw new Error(errorBody.detail || 'Failed to unlink user.');
        }
        await fetchStatuses();
      } catch (err) {
        setError(`Failed to unlink: ${err.message}`);
      }
    }
  };

  if (error) {
    return <div>Error: {error}</div>;
  }

  const selectedConfig = configs.find(c => c.filename === selectedFile);
  const status = selectedConfig?.status || 'disconnected';

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected':
        return 'green';
      case 'linking':
      case 'initializing':
      case 'got qr code':
        return 'orange';
      case 'disconnected':
      case 'invalid_config':
        return 'gray';
      default:
        return 'gray'; // Default for unknown statuses
    }
  };

  return (
    <div>
      <h2>Configuration Files</h2>
      <div className="file-list-container">
        {configs.length === 0 ? (
          <p>No configuration files found.</p>
        ) : (
          <ul className="file-list">
            {configs.map(config => (
              <li
                key={config.filename}
                className={`file-item ${selectedFile === config.filename ? 'selected' : ''}`}
                onClick={() => setSelectedFile(config.filename)}
              >
                <span className={`status-dot ${getStatusColor(config.status)}`}></span>
                {config.filename}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="action-buttons">
        <button onClick={handleAdd}>
          Add
        </button>

        {status === 'connected' ? (
          <button onClick={handleUnlink} disabled={!selectedFile} className="unlink-button">
            Unlink
          </button>
        ) : (
          <button onClick={handleLink} disabled={!selectedFile || isLinking || status !== 'disconnected'}>
            {isLinking ? 'Linking...' : 'Link'}
          </button>
        )}

        <button onClick={handleEdit} disabled={!selectedFile}>
          Edit
        </button>
        <button onClick={handleDelete} disabled={!selectedFile} className="delete-button">
          Delete
        </button>
      </div>
    </div>
  );
}

export default HomePage;
