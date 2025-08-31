import React, { useState, useEffect } from 'react';

function App() {
  const [instanceId, setInstanceId] = useState(null);
  const [status, setStatus] = useState(null);
  const [qrCode, setQrCode] = useState(null);

  const createUser = async () => {
    // Hardcoded user data for now
    const userData = [
      {
        "user_id": "user_wa_1",
        "respond_to_whitelist": ["1234567890"],
        "chat_provider_config": {
          "provider_name": "whatsAppBaileyes",
          "provider_config": {
            "allow_group_messages": false
          }
        },
        "queue_config": {
          "max_messages": 10,
          "max_characters": 1000,
          "max_days": 1
        },
        "llm_provider_config": {
          "provider_name": "dummy",
          "provider_config": {}
        }
      }
    ];

    try {
      const response = await fetch('/chatbot', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });
      const data = await response.json();
      if (data && data.length > 0) {
        setInstanceId(data[0].instance_id);
      }
    } catch (error) {
      console.error('Error creating user:', error);
    }
  };

  useEffect(() => {
    if (instanceId) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(`/chatbot/${instanceId}/status`);
          const data = await response.json();
          setStatus(data.status);
          if (data.qr) {
            setQrCode(data.qr);
          }
        } catch (error) {
          console.error('Error fetching status:', error);
        }
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [instanceId]);

  return (
    <div>
      <h1>WhatsApp Imposter Control Panel</h1>
      {!instanceId ? (
        <button onClick={createUser}>Create User</button>
      ) : (
        <div>
          <h2>User Created!</h2>
          <p>Instance ID: {instanceId}</p>
          <p>Status: {status}</p>
          {qrCode && <img src={qrCode} alt="QR Code" />}
        </div>
      )}
    </div>
  );
}

export default App;
