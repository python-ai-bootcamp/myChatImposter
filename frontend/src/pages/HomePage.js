import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function HomePage() {
  const [configs, setConfigs] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchStatuses = async () => {
    try {
      const response = await fetch('/api/configurations/status');
      if (!response.ok) {
        setError('Failed to fetch configuration statuses.');
        return;
      }
      const data = await response.json();
      setConfigs(data.configurations || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchStatuses();
    const interval = setInterval(fetchStatuses, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleLink = async () => {
    if (!selectedUserId) return;

    setIsLinking(true);
    setError(null);

    try {
      const configResponse = await fetch(`/api/configurations/${selectedUserId}`);
      if (!configResponse.ok) {
        throw new Error('Failed to fetch configuration.');
      }
      const configData = await configResponse.json();

      const payload = Array.isArray(configData) ? configData[0] : configData;
      const createResponse = await fetch('/chatbot', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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
      navigate(`/link/${userId}`);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLinking(false);
    }
  };

  const handleEdit = () => {
    if (selectedUserId) {
      navigate(`/edit/${selectedUserId}`);
    }
  };

  const handleAdd = () => {
    const userId = prompt('Enter a new unique user_id:');
    if (!userId) {
      return;
    }

    if (configs.some(c => c.user_id === userId)) {
      alert(`Configuration with user_id "${userId}" already exists.`);
      return;
    }

    navigate(`/edit/${userId}`, { state: { isNew: true } });
  };

  const handleDelete = async () => {
    if (!selectedUserId) {
      return;
    }

    if (window.confirm(`Are you sure you want to delete the configuration for "${selectedUserId}"?`)) {
      try {
        const response = await fetch(`/api/configurations/${selectedUserId}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          const errorBody = await response.json();
          throw new Error(errorBody.detail || 'Failed to delete configuration.');
        }

        setSelectedUserId(null);
        await fetchStatuses();
      } catch (err) {
        setError(`Failed to delete configuration: ${err.message}`);
      }
    }
  };

  const handleUnlink = async () => {
    if (!selectedUserId) return;

    if (window.confirm(`Are you sure you want to unlink user "${selectedUserId}"?`)) {
      try {
        const response = await fetch(`/chatbot/${selectedUserId}`, {
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

  const selectedConfig = configs.find(c => c.user_id === selectedUserId);
  const status = selectedConfig?.status || 'disconnected';

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'green';
      case 'linking':
      case 'initializing':
      case 'got qr code':
      case 'waiting': return 'orange';
      case 'disconnected':
      case 'invalid_config': return 'gray';
      default: return 'gray';
    }
  };

  const pageStyle = {
    maxWidth: '600px',
    margin: '40px auto',
    padding: '2rem',
    backgroundColor: '#fff',
    border: '1px solid #ccc',
    borderRadius: '8px',
    boxShadow: '0 4px 8px rgba(0,0,0,0.1)'
  };

  return (
    <div style={pageStyle}>
      <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>User Configurations</h2>
      <div className="file-list-container">
        {configs.length === 0 ? (
          <p>No configurations found.</p>
        ) : (
          <ul className="file-list">
            {configs.map(config => (
              <li
                key={config.user_id}
                className={`file-item ${selectedUserId === config.user_id ? 'selected' : ''}`}
                onClick={() => setSelectedUserId(config.user_id)}
              >
                <span className={`status-dot ${getStatusColor(config.status)}`}></span>
                {config.user_id}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="action-buttons" style={{ marginTop: '2rem' }}>
        <button onClick={handleAdd}>
          Add
        </button>

        {status === 'connected' ? (
          <button onClick={handleUnlink} disabled={!selectedUserId} className="unlink-button">
            Unlink
          </button>
        ) : (
          <button onClick={handleLink} disabled={!selectedUserId || isLinking || status !== 'disconnected'}>
            {isLinking ? 'Linking...' : 'Link'}
          </button>
        )}

        <button onClick={handleEdit} disabled={!selectedUserId}>
          Edit
        </button>
        <button onClick={handleDelete} disabled={!selectedUserId} className="delete-button">
          Delete
        </button>
      </div>
    </div>
  );
}

export default HomePage;
