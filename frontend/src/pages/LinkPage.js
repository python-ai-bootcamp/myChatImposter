import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';

function LinkPage() {
  const { filename } = useParams();
  const effectRan = useRef(false);
  const [userId, setUserId] = useState(null);
  const [status, setStatus] = useState('Initializing...');
  const [qrCode, setQrCode] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (effectRan.current === true) {
      return;
    }
    effectRan.current = true;

    let pollInterval;

    const createAndPoll = async () => {
      try {
        // 1. Fetch the configuration
        const configResponse = await fetch(`/api/configurations/${filename}`);
        if (!configResponse.ok) {
          throw new Error('Failed to fetch configuration.');
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
            throw new Error(`Failed to create user: ${errorBody.detail || createResponse.statusText}`);
        }

        const createData = await createResponse.json();

        if (createData.failed && createData.failed.length > 0) {
            throw new Error(`Failed to create instance: ${createData.failed[0].error}`);
        }

        const newUserId = createData.successful[0].user_id;
        setUserId(newUserId);
        setStatus('Instance created. Waiting for status...');

        // 3. Start polling for status
        pollInterval = setInterval(async () => {
          try {
            const statusResponse = await fetch(`/chatbot/${newUserId}/status`);
            if (!statusResponse.ok) {
                if(statusResponse.status === 404){
                    setError("Instance not found. It might have been terminated or the server restarted.");
                    clearInterval(pollInterval);
                }
                return;
            }
            const statusData = await statusResponse.json();
            setStatus(statusData.status || 'Polling...');
            if (statusData.qr) {
              setQrCode(statusData.qr);
            }
            if (statusData.status === 'CONNECTED' || statusData.status === 'ERROR') {
                clearInterval(pollInterval);
            }
          } catch (pollErr) {
            setError('Error polling for status.');
            clearInterval(pollInterval);
          }
        }, 2000);

      } catch (err) {
        setError(err.message);
      }
    };

    createAndPoll();

    // Return the cleanup function for when the component unmounts
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [filename]);

  return (
    <div>
      <h2>Link Device for: {filename}</h2>
      {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      {userId && <p>User ID: {userId}</p>}
      <p>Status: {status}</p>
      {qrCode && <img src={qrCode} alt="QR Code" />}
    </div>
  );
}

export default LinkPage;
