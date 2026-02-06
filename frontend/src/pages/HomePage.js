import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import UserTable from '../components/UserTable';
import LinkUserModal from '../components/LinkUserModal';
import CreateUserModal from '../components/CreateUserModal';
import { isActionEnabled } from '../utils/actionHelpers';

const HomePage = ({ enableFiltering, showOwnerColumn }) => {
  const [configs, setConfigs] = useState([]);
  const [selectedBotId, setSelectedBotId] = useState(null);
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState(null);

  // QR Code / Linking Modal State
  const [linkingBotId, setLinkingBotId] = useState(null);
  const [qrCode, setQrCode] = useState(null);

  // Create User Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [linkStatus, setLinkStatus] = useState(null);

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const pollIntervalRef = useRef(null);

  // Handle Root Redirection
  useEffect(() => {
    if (window.location.pathname === '/') {
      const role = sessionStorage.getItem('role');
      if (role === 'admin') {
        navigate('/admin/home', { replace: true });
      } else if (role === 'user') {
        navigate('/user/home', { replace: true });
      } else {
        navigate('/login', { replace: true });
      }
    }
  }, [navigate]);

  const fetchStatuses = useCallback(async () => {
    try {
      // If we are at root, don't fetch, let redirect happen
      if (window.location.pathname === '/') return;

      const endpoint = '/api/external/bots/status';

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
    const autoLinkBotId = searchParams.get('auto_link');
    if (autoLinkBotId) {
      setLinkingBotId(autoLinkBotId);
      setLinkStatus('Initializing...');
      setIsLinking(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Polling for specific user status (QR code) when modal is open
  useEffect(() => {
    if (linkingBotId) {
      const pollSpecificStatus = async () => {
        try {
          const response = await fetch(`/api/external/bots/${linkingBotId}/status`);
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
  }, [linkingBotId]);

  const handleLink = async (botId) => {
    setIsLinking(true);
    setError(null);
    setLinkingBotId(botId);
    setLinkStatus('Initializing...');

    try {
      const selectedConfig = configs.find(c => c.bot_id === botId);
      const status = selectedConfig?.status || 'disconnected';

      if (status === 'disconnected') {
        const createResponse = await fetch(`/api/external/bots/${botId}/actions/link`, {
          method: 'POST',
        });
        if (!createResponse.ok) {
          const errorBody = await createResponse.json();
          throw new Error(errorBody.detail || `Failed to create session (HTTP ${createResponse.status})`);
        }
      } else {
        const reloadResponse = await fetch(`/api/external/bots/${botId}/actions/reload`, {
          method: 'POST',
        });
        if (!reloadResponse.ok) {
          const errorBody = await reloadResponse.json();
          throw new Error(errorBody.detail || 'Failed to reload configuration.');
        }
      }
    } catch (err) {
      setError(err.message);
      setLinkingBotId(null);
    } finally {
      setIsLinking(false);
    }
  };

  const handleUnlink = async (botId) => {
    if (window.confirm(`Are you sure you want to unlink bot "${botId}"?`)) {
      try {
        const response = await fetch(`/api/external/bots/${botId}/actions/unlink`, {
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

  const handleDelete = async (botId) => {
    if (window.confirm(`Are you sure you want to delete the configuration for "${botId}"?`)) {
      try {
        const role = sessionStorage.getItem('role');
        const endpoint = role === 'admin'
          ? `/api/external/bots/${botId}`
          : `/api/external/ui/bots/${botId}`;

        const response = await fetch(endpoint, {
          method: 'DELETE',
        });
        if (!response.ok) {
          const errorBody = await response.json();
          throw new Error(errorBody.detail || 'Failed to delete configuration.');
        }
        setSelectedBotId(null);
        await fetchStatuses();
      } catch (err) {
        setError(`Failed to delete configuration: ${err.message}`);
      }
    }
  };

  const handleAdd = () => {
    setIsCreateModalOpen(true);
  };

  const handleCreateConfirm = (botId) => {
    setIsCreateModalOpen(false);
    const role = sessionStorage.getItem('role');
    if (role === 'admin') {
      navigate(`/admin/edit/${botId}`, { state: { isNew: true } });
    } else {
      navigate(`/user/edit/${botId}`, { state: { isNew: true } });
    }
  };

  const handleEdit = (botId) => {
    const role = sessionStorage.getItem('role');
    if (role === 'admin') {
      navigate(`/admin/edit/${botId}`);
    } else {
      navigate(`/user/edit/${botId}`);
    }
  };

  const closeModal = () => {
    setLinkingBotId(null);
  };

  const selectedConfig = configs.find(c => c.bot_id === selectedBotId);
  const status = selectedConfig?.status || 'disconnected';

  // Styles
  const pageStyle = {
    maxWidth: '1200px', // Wider to accommodate filters if needed
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
    borderTop: '1px solid #dee2e6',
    marginBottom: '20px' // Ensure separation from bottom visual edge
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
      <h2 style={{ margin: 0, marginBottom: '1rem' }}>Bot Configurations</h2>

      {error && <div style={{ color: 'red', marginTop: '1rem', padding: '10px', backgroundColor: '#fff5f5', borderRadius: '4px' }}>Error: {error}</div>}

      <UserTable
        configs={configs}
        selectedBotId={selectedBotId}
        onSelectBot={setSelectedBotId}
        enableFiltering={enableFiltering}
        showOwnerColumn={showOwnerColumn}
      />

      <div style={actionButtonsContainerStyle}>
        <button onClick={handleAdd} style={getButtonStyle('primary', false)}>
          Add
        </button>

        {status === 'connected' ? (
          <button
            onClick={() => handleUnlink(selectedBotId)}
            disabled={!isActionEnabled('unlink', status, selectedBotId)}
            style={getButtonStyle('warning', !isActionEnabled('unlink', status, selectedBotId))}
          >
            Unlink
          </button>
        ) : (
          <button
            onClick={() => handleLink(selectedBotId)}
            disabled={!isActionEnabled('link', status, selectedBotId) || isLinking}
            style={getButtonStyle('success', !isActionEnabled('link', status, selectedBotId) || isLinking)}
          >
            {isLinking && linkingBotId === selectedBotId ? 'Linking...' : 'Link'}
          </button>
        )}

        <button
          onClick={() => handleEdit(selectedBotId)}
          disabled={!isActionEnabled('edit', status, selectedBotId)}
          style={getButtonStyle('primary', !isActionEnabled('edit', status, selectedBotId))}
        >
          Edit
        </button>

        <button
          onClick={() => handleDelete(selectedBotId)}
          disabled={!isActionEnabled('delete', status, selectedBotId)}
          style={getButtonStyle('danger', !isActionEnabled('delete', status, selectedBotId))}
        >
          Delete
        </button>
      </div>

      <LinkUserModal
        linkingBotId={linkingBotId}
        linkStatus={linkStatus}
        qrCode={qrCode}
        onClose={closeModal}
      />

      <CreateUserModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onConfirm={handleCreateConfirm}
      />
    </div>
  );
}

export default HomePage;
