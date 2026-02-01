import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

function HomePage() {
  const [configs, setConfigs] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [isLinking, setIsLinking] = useState(false);
  const [error, setError] = useState(null);

  // QR Code / Linking Modal State
  const [linkingUser, setLinkingUser] = useState(null); // The user currently being linked/viewed
  const [qrCode, setQrCode] = useState(null);
  const [linkStatus, setLinkStatus] = useState(null);

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const pollIntervalRef = useRef(null);

  const fetchStatuses = useCallback(async () => {
    try {
      // Get user role and ID from sessionStorage
      const role = sessionStorage.getItem('role');
      const userId = sessionStorage.getItem('user_id');

      // Admin sees all users, regular users see only themselves
      const endpoint = role === 'admin'
        ? '/api/external/users/status'           // Admin: all users
        : `/api/external/users/${userId}/info`;  // Regular user: only self

      const response = await fetch(endpoint);
      if (!response.ok) {
        // Handle 401 - redirect to login
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        // limit error noise if it's just a transient issue, or handle gracefully
        console.error('Failed to fetch configuration statuses.');
        return;
      }
      const data = await response.json();
      setConfigs(data.configurations || []);
      // Clear global error if fetch succeeds
      if (error === 'Failed to fetch configuration statuses.') setError(null);
    } catch (err) {
      console.error(err);
      // specific error handling if needed
    }
  }, [navigate, error]);

  useEffect(() => {
    fetchStatuses();
    const interval = setInterval(fetchStatuses, 3000);

    return () => clearInterval(interval);
  }, [fetchStatuses]);

  // Dedicated effect for handling auto-link navigation state (via Query Params)
  useEffect(() => {
    const autoLinkUser = searchParams.get('auto_link');

    if (autoLinkUser) {
      setLinkingUser(autoLinkUser);
      setLinkStatus('Initializing...');
      setIsLinking(true);

      // Clear the query param to prevent re-triggering
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Polling for specific user status (QR code) when the modal is open
  useEffect(() => {

    // console.log(`[Frontend] linkingUser changed to: ${linkingUser}`);
    if (linkingUser) {
      const pollSpecificStatus = async () => {
        try {
          // Heartbeat is handled by backend logic on this endpoint
          const response = await fetch(`/api/external/users/${linkingUser}/status`);
          if (response.ok) {
            const data = await response.json();
            setLinkStatus(data.status);
            setQrCode(data.qr || null);

            if (data.status?.toLowerCase() === 'connected') {
              // If connected, we can potentially close the modal after a delay or let user close it
              // For now, keep it open to show success
            }
          }
        } catch (err) {
          console.error('Error polling specific status:', err);
        }
      };

      pollSpecificStatus(); // Initial call
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

    // Open the modal immediately to show progress
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
        // If 'close' or 'error', reload
        const reloadResponse = await fetch(`/api/external/users/${userId}/actions/reload`, {
          method: 'POST',
        });
        if (!reloadResponse.ok) {
          const errorBody = await reloadResponse.json();
          throw new Error(errorBody.detail || 'Failed to reload configuration.');
        }
      }

      // The useEffect will pick up the polling
    } catch (err) {
      setError(err.message);
      setLinkingUser(null); // Close modal on error start
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

        setSelectedUserId(null); // Clear selection if deleted
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

    navigate(`/edit/${userId}`, { state: { isNew: true } });
  };

  const handleEdit = (userId) => {
    navigate(`/edit/${userId}`);
  };

  const closeModal = () => {
    setLinkingUser(null);
  };

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

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '1.5rem',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    borderRadius: '8px',
    overflow: 'hidden'
  };

  const thStyle = {
    backgroundColor: '#f8f9fa',
    color: '#495057',
    fontWeight: '600',
    padding: '12px 15px',
    textAlign: 'left',
    borderBottom: '2px solid #dee2e6'
  };

  const tdStyle = {
    padding: '12px 15px',
    borderBottom: '1px solid #dee2e6',
    verticalAlign: 'middle',
    textAlign: 'left'
  };

  const trStyle = (userId) => ({
    backgroundColor: selectedUserId === userId ? '#e9ecef' : '#fff',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  });

  const modalOverlayStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000
  };

  const modalContentStyle = {
    backgroundColor: '#1a1a1a',
    padding: '0',
    borderRadius: '45px',
    maxWidth: '320px',
    width: '90%',
    textAlign: 'center',
    boxShadow: '0 25px 50px rgba(0,0,0,0.5), inset 0 0 0 3px #333',
    position: 'relative',
    overflow: 'hidden',
    border: '8px solid #1a1a1a'
  };

  const phoneScreenStyle = {
    backgroundColor: '#000',
    borderRadius: '35px',
    margin: '10px',
    padding: '20px',
    minHeight: '500px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative'
  };

  const notchStyle = {
    position: 'absolute',
    top: '10px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '100px',
    height: '25px',
    backgroundColor: '#1a1a1a',
    borderRadius: '20px'
  };

  const homeIndicatorStyle = {
    position: 'absolute',
    bottom: '8px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '130px',
    height: '5px',
    backgroundColor: '#555',
    borderRadius: '3px'
  };

  const actionButtonsContainerStyle = {
    display: 'flex',
    gap: '1rem',
    marginTop: '2rem',
    paddingTop: '1rem',
    borderTop: '1px solid #dee2e6'
  };

  // Button Style Helper
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



      <div style={{ overflowX: 'auto' }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>User Name</th>
              <th style={thStyle}>Authenticated</th>
              <th style={thStyle}>Linked</th>
            </tr>
          </thead>
          <tbody>
            {configs.length === 0 ? (
              <tr>
                <td colSpan="3" style={{ ...tdStyle, textAlign: 'center', color: '#6c757d' }}>No configurations found.</td>
              </tr>
            ) : (
              configs.map(config => (
                <tr
                  key={config.user_id}
                  style={trStyle(config.user_id)}
                  onClick={() => setSelectedUserId(config.user_id)}
                >
                  <td style={tdStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {config.user_id}
                    </div>
                  </td>
                  <td style={tdStyle}>
                    {config.authenticated ? (
                      <span style={{ color: 'green', fontWeight: 'bold' }}>Yes</span>
                    ) : (
                      <span style={{ color: '#6c757d' }}>No</span>
                    )}
                  </td>
                  <td style={tdStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span
                        className={`status-dot ${getStatusColor(config.status)}`}
                        style={{
                          height: '10px',
                          width: '10px',
                          backgroundColor: getStatusColor(config.status),
                          borderRadius: '50%',
                          display: 'inline-block'
                        }}></span>
                      {config.status}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div style={actionButtonsContainerStyle}>
        <button onClick={handleAdd} style={getButtonStyle('primary', false)}>
          Add
        </button>

        {status === 'connected' ? (
          <button
            onClick={() => handleUnlink(selectedUserId)}
            disabled={!selectedUserId}
            style={getButtonStyle('warning', !selectedUserId)}
          >
            Unlink
          </button>
        ) : (
          <button
            onClick={() => handleLink(selectedUserId)}
            disabled={!selectedUserId || isLinking || !['disconnected', 'close', 'error', 'initializing', 'waiting', 'got qr code'].includes(status)}
            style={getButtonStyle('success', !selectedUserId || isLinking || !['disconnected', 'close', 'error', 'initializing', 'waiting', 'got qr code'].includes(status))}
          >
            {isLinking && linkingUser === selectedUserId ? 'Linking...' : 'Link'}
          </button>
        )}

        <button
          onClick={() => handleEdit(selectedUserId)}
          disabled={!selectedUserId}
          style={getButtonStyle('primary', !selectedUserId)}
        >
          Edit
        </button>

        <button
          onClick={() => handleDelete(selectedUserId)}
          disabled={!selectedUserId}
          style={getButtonStyle('danger', !selectedUserId)}
        >
          Delete
        </button>
      </div>

      {/* QR Code / Status Modal - iPhone Style */}
      {linkingUser && (
        <div style={modalOverlayStyle} onClick={closeModal}>
          <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
            <div style={phoneScreenStyle}>
              {/* Notch */}
              <div style={notchStyle}></div>

              {/* Close button */}
              <button
                onClick={closeModal}
                style={{
                  position: 'absolute',
                  top: '45px',
                  right: '15px',
                  background: 'rgba(255,255,255,0.2)',
                  border: 'none',
                  fontSize: '1.2rem',
                  cursor: 'pointer',
                  color: '#fff',
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                &times;
              </button>

              {/* Content */}
              <div style={{ marginTop: '30px', color: '#fff' }}>
                <h3 style={{ margin: '0 0 10px 0', color: '#fff', fontSize: '1.1rem' }}>
                  {linkingUser}
                </h3>
                <p style={{ margin: '0 0 20px 0', color: '#888', fontSize: '0.85rem' }}>
                  {linkStatus || 'Initializing...'}
                </p>

                {qrCode ? (
                  <div>
                    <div style={{
                      backgroundColor: '#fff',
                      padding: '15px',
                      borderRadius: '12px',
                      display: 'inline-block'
                    }}>
                      <img
                        src={qrCode}
                        alt="QR Code"
                        style={{
                          width: '180px',
                          height: '180px',
                          display: 'block'
                        }}
                      />
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '15px' }}>
                      Scan with WhatsApp
                    </p>
                  </div>
                ) : (
                  <div style={{
                    padding: '40px 20px',
                    color: linkStatus === 'connected' ? '#4ade80' : '#888'
                  }}>
                    {linkStatus === 'connected' ? (
                      <div>
                        <div style={{ fontSize: '3rem', marginBottom: '10px' }}>✓</div>
                        <div>Connected!</div>
                      </div>
                    ) : (
                      <div>
                        <div style={{
                          width: '40px',
                          height: '40px',
                          border: '3px solid #444',
                          borderTop: '3px solid #888',
                          borderRadius: '50%',
                          margin: '0 auto 15px',
                          animation: 'spin 1s linear infinite'
                        }}></div>
                        <div>Connecting...</div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Home Indicator */}
              <div style={homeIndicatorStyle}></div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default HomePage;
