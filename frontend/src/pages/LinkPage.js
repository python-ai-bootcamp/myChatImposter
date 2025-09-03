import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

function LinkPage() {
  const { userId } = useParams(); // Changed from filename to userId
  const [status, setStatus] = useState('Checking status...');
  const [qrCode, setQrCode] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let pollInterval;

    const pollStatus = async () => {
      try {
        const statusResponse = await fetch(`/chatbot/${userId}/status`);
        if (!statusResponse.ok) {
            if(statusResponse.status === 404){
                setError(`No active session found for user "${userId}". It might have been terminated or the server restarted.`);
                clearInterval(pollInterval);
            }
            // For other errors, we can just let it retry
            return;
        }
        const statusData = await statusResponse.json();
        setStatus(statusData.status || 'Polling...');
        setQrCode(statusData.qr || null);

        // The 'connected' status indicates a successful, stable connection.
        if (statusData.status?.toLowerCase() === 'connected' || statusData.status === 'ERROR') {
            clearInterval(pollInterval);
        }
      } catch (pollErr) {
        setError('Error polling for status.');
        clearInterval(pollInterval);
      }
    };

    // Start polling immediately and then set an interval
    pollStatus();
    pollInterval = setInterval(pollStatus, 2000);

    // Return the cleanup function for when the component unmounts
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [userId]); // Effect depends on userId

  const pageStyle = {
    maxWidth: '600px',
    margin: '40px auto',
    textAlign: 'center'
  };

  return (
    <div style={pageStyle}>
      <h2>Link Status for User: {userId}</h2>
      {error && <div style={{ color: 'red', marginTop: '1rem' }}>Error: {error}</div>}
      <p style={{ fontSize: '1.2rem', margin: '1rem 0' }}>
        Status: <span style={{ fontWeight: 'bold' }}>{status}</span>
      </p>
      {qrCode && <img src={qrCode} alt="QR Code" style={{ marginTop: '1rem', border: '5px solid white', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }} />}
    </div>
  );
}

export default LinkPage;
