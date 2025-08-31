import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

function LinkPage() {
  const { filename } = useParams();
  const [instanceId, setInstanceId] = useState(null);
  const [status, setStatus] = useState('Initializing...');
  const [qrCode, setQrCode] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
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
          body: JSON.stringify([configData]), // API expects an array
        });

        if (!createResponse.ok) {
            const errorBody = await createResponse.json();
            throw new Error(`Failed to create user: ${errorBody.detail || createResponse.statusText}`);
        }

        const createData = await createResponse.json();

        if (createData.failed && createData.failed.length > 0) {
            throw new Error(`Failed to create instance: ${createData.failed[0].error}`);
        }

        const newInstanceId = createData.successful[0].instance_id;
        setInstanceId(newInstanceId);
        setStatus('Instance created. Waiting for status...');

        // 3. Start polling for status
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await fetch(`/chatbot/${newInstanceId}/status`);
            if (!statusResponse.ok) {
                // Stop polling if instance is not found (e.g., server restarted)
                if(statusResponse.status === 404){
                    setError("Instance not found. It might have been terminated or the server restarted.");
                    clearInterval(pollInterval);
                }
                return; // Continue polling on other errors
            }
            const statusData = await statusResponse.json();
            setStatus(statusData.status || 'Polling...');
            if (statusData.qr) {
              setQrCode(statusData.qr);
              // Optional: stop polling once we get a QR code or a final status
            }
            if (statusData.status === 'CONNECTED' || statusData.status === 'ERROR') {
                clearInterval(pollInterval);
            }
          } catch (pollErr) {
            setError('Error polling for status.');
            clearInterval(pollInterval);
          }
        }, 2000);

        // Cleanup function to stop polling when the component unmounts
        return () => clearInterval(pollInterval);

      } catch (err) {
        setError(err.message);
      }
    };

    createAndPoll();
    // The empty dependency array ensures this effect runs only once on mount.
  }, [filename]);

  return (
    <div>
      <h2>Link Device for: {filename}</h2>
      {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      {instanceId && <p>Instance ID: {instanceId}</p>}
      <p>Status: {status}</p>
      {qrCode && <img src={qrCode} alt="QR Code" />}
    </div>
  );
}

export default LinkPage;
