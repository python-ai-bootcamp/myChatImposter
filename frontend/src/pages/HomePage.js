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
        const selectedConfig = configs.find(c => c.user_id === selectedUserId);
        const status = selectedConfig?.status || 'disconnected';

        if (status === 'disconnected') {
            // If the user is fully disconnected, we need to create a new session.
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
        } else {
            // If the status is 'close' or 'error', the instance exists but is not running.
            // We should reload it to restart the connection process.
            const reloadResponse = await fetch(`/chatbot/${selectedUserId}/reload`, {
                method: 'POST',
            });

            if (!reloadResponse.ok) {
                const errorBody = await reloadResponse.json();
                throw new Error(errorBody.detail || 'Failed to reload configuration.');
            }
        }

        // If either action is successful, navigate to the link page.
        navigate(`/link/${selectedUserId}`);

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
          <button onClick={handleLink} disabled={!selectedUserId || isLinking || !['disconnected', 'close', 'error'].includes(status)}>
            {isLinking ? 'Linking...' : 'Link'}
          </button>
        )}

        <button onClick={handleEdit} disabled={!selectedUserId}>
          Edit
        </button>
        <button onClick={handleDelete} disabled={!selectedUserId} className="delete-button">
          Delete
        </button>
        <button
            onClick={() => {
                if (selectedUserId) {
                    navigate(`/tracking/${selectedUserId}`);
                }
            }}
            disabled={!selectedUserId || status !== 'connected'}
            style={{ backgroundColor: (!selectedUserId || status !== 'connected') ? '#6c757d' : '#007bff' }}
        >
            Group Tracking
        </button>
      </div>
    </div>
  );
}

export default HomePage;
