import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import GenericTable from '../components/GenericTable';
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
  // ... (keep existing state/effects) ...

  // Helper for status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'green';
      case 'linking':
      case 'connecting':
      case 'initializing':
      case 'got qr code':
      case 'waiting': return 'orange';
      case 'disconnected':
      case 'invalid_config': return 'gray';
      default: return 'gray';
    }
  };

  const columns = [
    { key: 'bot_id', label: 'Bot ID', sortable: true, filterable: true, width: showOwnerColumn ? '25%' : '35%' },
    ...(showOwnerColumn ? [{ key: 'owner', label: 'Owner', sortable: true, filterable: true, width: '25%' }] : []),
    {
      key: 'authenticated',
      label: 'Authenticated',
      sortable: true,
      filterable: true,
      width: '15%',
      getValue: (item) => item.authenticated ? 'Yes' : 'No',
      render: (item) => item.authenticated ? <span style={{ color: 'green', fontWeight: 'bold' }}>Yes</span> : <span style={{ color: '#6c757d' }}>No</span>
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      filterable: true,
      customFilter: (value, filter) => value.startsWith(filter), // Enforce prefix matching via custom function
      width: showOwnerColumn ? '35%' : '50%',
      getValue: (item) => String(item.status || ''),
      render: (item) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            height: '10px',
            width: '10px',
            backgroundColor: getStatusColor(item.status),
            borderRadius: '50%',
            display: 'inline-block'
          }}></span>
          {item.status}
        </div>
      )
    }
  ];

  // ... (keep hooks) ...
  const [searchParams, setSearchParams] = useSearchParams();
  const pollIntervalRef = useRef(null);

  // Handle Root Redirection
  useEffect(() => {
    if (window.location.pathname === '/') {
      const role = sessionStorage.getItem('role');
      if (role === 'admin') {
        navigate('/admin/home', { replace: true });
      } else if (role === 'user') {
        navigate('/operator/dashboard', { replace: true });
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

      const response = await fetch(endpoint, { credentials: 'include' });
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
          const response = await fetch(`/api/external/bots/${linkingBotId}/status`, { credentials: 'include' });
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
      navigate(`/operator/bot/${botId}`, { state: { isNew: true } });
    }
  };

  const handleEdit = (botId) => {
    const role = sessionStorage.getItem('role');
    if (role === 'admin') {
      navigate(`/admin/edit/${botId}`);
    } else {
      navigate(`/operator/bot/${botId}`);
    }
  };

  const closeModal = () => {
    setLinkingBotId(null);
  };

  const selectedConfig = configs.find(c => c.bot_id === selectedBotId);
  const status = selectedConfig?.status || 'disconnected';

  // Dark glassmorphism styles matching Profile page
  const pageStyle = {
    // 60px is the height of the fixed GlobalHeader
    height: 'calc(100vh - 60px)',
    width: '100vw',
    fontFamily: "'Inter', 'system-ui', sans-serif",
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '3rem 2rem', // Increased vertical padding
    background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)',
    position: 'relative',
    overflow: 'hidden',
    boxSizing: 'border-box',
    flexDirection: 'column', // Stack vertically
  };

  // Base glass style shared by both panels
  const glassBase = {
    background: 'rgba(30, 41, 59, 0.5)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(20px)',
    width: '100%',
    maxWidth: '1200px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    boxSizing: 'border-box',
  };

  const headerPanelStyle = {
    ...glassBase,
    padding: '1.5rem',
    borderRadius: '1.5rem',
    borderBottomLeftRadius: '0.3rem', // Sharper connection
    borderBottomRightRadius: '0.3rem', // Sharper connection
    marginBottom: '10px', // Increased gap
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    zIndex: 20,
  };

  // Calculate stable height based on UNFILTERED data count
  // 5 rows min (approx 350px) -> ~60px per row + ~120px overhead (header/footer/padding)
  // Updated to 450 min / 180 overhead to accommodate buttons + table minHeight (300px) + Generous buffer
  const estimatedHeight = Math.max(450, (configs.length * 60) + 180);

  const bodyPanelStyle = {
    ...glassBase,
    padding: '1rem',
    borderRadius: '1.5rem',
    borderTopLeftRadius: '0.3rem', // Sharper connection
    borderTopRightRadius: '0.3rem', // Sharper connection
    // Use min() to cap at screen height, but otherwise stick to estimated height
    height: `min(calc(100vh - 16rem), ${estimatedHeight}px)`,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    zIndex: 10,
  };

  const headerStyle = {
    fontSize: '2.5rem',
    fontWeight: 800,
    margin: 0,
    background: 'linear-gradient(to right, #c084fc, #6366f1)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    textShadow: '0 10px 20px rgba(0,0,0,0.2)',
  };

  const actionButtonsContainerStyle = {
    display: 'flex',
    gap: '1rem',
    marginTop: '1rem',
    paddingTop: '1rem',
    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
    flexShrink: 0,
  };

  // ... button styles ...

  const getButtonStyle = (type, disabled) => {
    // ... existing ... 
    const base = {
      padding: '10px 20px',
      fontSize: '0.9rem',
      fontWeight: 600,
      border: 'none',
      borderRadius: '0.75rem',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      transition: 'all 0.2s ease',
      boxShadow: disabled ? 'none' : '0 4px 12px rgba(0, 0, 0, 0.3)',
    };
    const styles = {
      primary: { ...base, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white' },
      success: { ...base, background: 'linear-gradient(135deg, #22c55e, #16a34a)', color: 'white' },
      warning: { ...base, background: 'linear-gradient(135deg, #f59e0b, #d97706)', color: 'white' },
      danger: { ...base, background: 'linear-gradient(135deg, #ef4444, #dc2626)', color: 'white' },
    };
    return styles[type] || base;
  };

  return (
    <div style={pageStyle} >
      {/* Detached Header Panel */}
      < div style={headerPanelStyle} >
        <h2 style={headerStyle}>Bot Configurations</h2>
      </div >

      {/* Body Panel */}
      < div style={bodyPanelStyle} >
        {error && <div style={{ color: '#fca5a5', marginBottom: '1rem', padding: '12px', backgroundColor: 'rgba(239, 68, 68, 0.2)', borderRadius: '0.5rem', border: '1px solid rgba(239, 68, 68, 0.3)' }}>Error: {error}</div>}

        <GenericTable
          data={configs}
          columns={columns}
          idField="bot_id"
          selectedId={selectedBotId}
          onSelect={setSelectedBotId}
          enableFiltering={enableFiltering}
          darkMode={true}
          style={{ marginTop: '0', flex: 1, minHeight: '300px' }}
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
      </div >
    </div >
  );
}

export default HomePage;
