import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import UserTable from '../components/UserTable';
import LinkUserModal from '../components/LinkUserModal';
import { isActionEnabled } from '../utils/actionHelpers';

function HomePage() {
  const [configs, setConfigs] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState(null);

  // QR Code / Linking Modal State
  const [linkingUser, setLinkingUser] = useState(null);
  const [qrCode, setQrCode] = useState(null);
  const [linkStatus, setLinkStatus] = useState(null);

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const pollIntervalRef = useRef(null);

  const fetchStatuses = useCallback(async () => {
    try {
      const role = sessionStorage.getItem('role');
      const userId = sessionStorage.getItem('user_id');
      const endpoint = '/api/external/users/status';

      const response = await fetch(endpoint);
      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        console.error('Failed to fetch configuration statuses.');
        return;
      }
      const data = await response.json();
      setConfigs(data.configurations || []);
      if (error === 'Failed to fetch configuration statuses.') setError(null);
    } catch (err) {
      console.error(err);
    }
  }, [navigate, error]);

  useEffect(() => {
    fetchStatuses();
    const interval = setInterval(fetchStatuses, 3000);
    return () => clearInterval(interval);
  }, [fetchStatuses]);

  // Handle auto-link navigation state (via Query Params)
  useEffect(() => {
    const autoLinkUser = searchParams.get('auto_link');
    if (autoLinkUser) {
      setLinkingUser(autoLinkUser);
      setLinkStatus('Initializing...');
      setIsLinking(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Polling for specific user status (QR code) when modal is open
  useEffect(() => {
    if (linkingUser) {
      const pollSpecificStatus = async () => {
        try {
          const response = await fetch(`/api/external/users/${linkingUser}/status`);
          if (response.ok) {
            const data = await response.json();
            setLinkStatus(data.status);
            setQrCode(data.qr || null);
          }
        } catch (err) {
          console.error('Error polling specific status:', err);
        }
      };

      pollSpecificStatus();
      pollIntervalRef.current = setInterval(pollSpecificStatus, 2000);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setQrCode(null);
      setLinkStatus(null);
    }

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [linkingUser]);

  const handleLink = async (userId) => {
    setIsLinking(true);
    setError(null);
    setLinkingUser(userId);
    setLinkStatus('Initializing...');

    try {
      const selectedConfig = configs.find(c => c.user_id === userId);
      const status = selectedConfig?.status || 'disconnected';

      if (status === 'disconnected') {
        const createResponse = await fetch(`/api/external/users/${userId}/actions/link`, {
          method: 'POST',
        });
        if (!createResponse.ok) {
          const errorBody = await createResponse.json();
          throw new Error(errorBody.detail || `Failed to create session (HTTP ${createResponse.status})`);
        }
      } else {
        const reloadResponse = await fetch(`/api/external/users/${userId}/actions/reload`, {
          method: 'POST',
        });
        if (!reloadResponse.ok) {
          const errorBody = await reloadResponse.json();
          throw new Error(errorBody.detail || 'Failed to reload configuration.');
        }
      }
    } catch (err) {
      setError(err.message);
      setLinkingUser(null);
    } finally {
      setIsLinking(false);
    }
  };

  const handleUnlink = async (userId) => {
    if (window.confirm(`Are you sure you want to unlink user "${userId}"?`)) {
      try {
        const response = await fetch(`/api/external/users/${userId}/actions/unlink`, {
          method: 'POST',
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

  const handleDelete = async (userId) => {
    if (window.confirm(`Are you sure you want to delete the configuration for "${userId}"?`)) {
      try {
        const response = await fetch(`/api/external/users/${userId}`, {
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

  const handleAdd = () => {
    const userId = prompt('Enter a new unique user_id:');
    if (!userId) return;
    if (configs.some(c => c.user_id === userId)) {
      alert(`Configuration with user_id "${userId}" already exists.`);
      return;
    }

    const role = sessionStorage.getItem('role');
    if (role === 'admin') {
      navigate(`/edit/${userId}`, { state: { isNew: true } });
    } else {
      navigate(`/user/edit/${userId}`, { state: { isNew: true } });
    }
  };

  const handleEdit = (userId) => {
    const role = sessionStorage.getItem('role');
    if (role === 'admin') {
      navigate(`/edit/${userId}`);
    } else {
      navigate(`/user/edit/${userId}`);
    }
  };

  const closeModal = () => {
    setLinkingUser(null);
  };

  const selectedConfig = configs.find(c => c.user_id === selectedUserId);
  const status = selectedConfig?.status || 'disconnected';

  // Styles
  const pageStyle = {
    maxWidth: '900px',
    margin: '40px auto',
    padding: '2rem',
    backgroundColor: '#fff',
    fontFamily: "'Inter', sans-serif",
  };

  const actionButtonsContainerStyle = {
    display: 'flex',
    gap: '1rem',
    marginTop: '2rem',
    paddingTop: '1rem',
    borderTop: '1px solid #dee2e6'
  };

  const getButtonStyle = (type, disabled) => {
    const base = {
      padding: '8px 16px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      borderRadius: '4px',
      fontSize: '0.9rem',
      transition: 'all 0.2s',
      opacity: disabled ? 0.6 : 1,
      backgroundColor: disabled ? '#e9ecef' : '#f8f9fa',
      color: disabled ? '#6c757d' : '#212529',
      border: disabled ? '1px solid #ced4da' : '1px solid #ccc'
    };

    if (disabled) return base;

    switch (type) {
      case 'primary':
        return { ...base, backgroundColor: '#007bff', color: 'white', border: 'none' };
      case 'danger':
        return { ...base, backgroundColor: '#dc3545', color: 'white', border: 'none' };
      case 'success':
        return { ...base, backgroundColor: '#28a745', color: 'white', border: 'none' };
      case 'warning':
        return { ...base, backgroundColor: '#ffc107', color: '#212529', border: 'none' };
      default:
        return base;
    }
  };

  return (
    <div style={pageStyle}>
      <h2 style={{ margin: 0, marginBottom: '1rem' }}>User Configurations</h2>

      {error && <div style={{ color: 'red', marginTop: '1rem', padding: '10px', backgroundColor: '#fff5f5', borderRadius: '4px' }}>Error: {error}</div>}

      <UserTable
        configs={configs}
        selectedUserId={selectedUserId}
        onSelectUser={setSelectedUserId}
      />

      <div style={actionButtonsContainerStyle}>
        <button onClick={handleAdd} style={getButtonStyle('primary', false)}>
          Add
        </button>

        {status === 'connected' ? (
          <button
            onClick={() => handleUnlink(selectedUserId)}
            disabled={!isActionEnabled('unlink', status, selectedUserId)}
            style={getButtonStyle('warning', !isActionEnabled('unlink', status, selectedUserId))}
          >
            Unlink
          </button>
        ) : (
          <button
            onClick={() => handleLink(selectedUserId)}
            disabled={!isActionEnabled('link', status, selectedUserId) || isLinking}
            style={getButtonStyle('success', !isActionEnabled('link', status, selectedUserId) || isLinking)}
          >
            {isLinking && linkingUser === selectedUserId ? 'Linking...' : 'Link'}
          </button>
        )}

        <button
          onClick={() => handleEdit(selectedUserId)}
          disabled={!isActionEnabled('edit', status, selectedUserId)}
          style={getButtonStyle('primary', !isActionEnabled('edit', status, selectedUserId))}
        >
          Edit
        </button>

        <button
          onClick={() => handleDelete(selectedUserId)}
          disabled={!isActionEnabled('delete', status, selectedUserId)}
          style={getButtonStyle('danger', !isActionEnabled('delete', status, selectedUserId))}
        >
          Delete
        </button>
      </div>

      <LinkUserModal
        linkingUser={linkingUser}
        linkStatus={linkStatus}
        qrCode={qrCode}
        onClose={closeModal}
      />
    </div>
  );
}

export default HomePage;
