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

        if (statusData.qr) {
          setQrCode(`data:image/png;base64,${statusData.qr}`);
        } else {
          setQrCode(null);
        }

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

  return (
    <div>
      <h2>Link Status for User: {userId}</h2>
      {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      <p>Status: {status}</p>
      {qrCode && <img src={qrCode} alt="QR Code" />}
    </div>
  );
}

export default LinkPage;
