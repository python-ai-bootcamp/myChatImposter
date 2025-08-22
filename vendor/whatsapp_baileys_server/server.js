const makeWASocket = require('@whiskeysockets/baileys').default;
const { DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const express = require('express');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const http = require('http');

// --- Globals ---
let sock;
let incomingMessages = []; // A simple in-memory queue for messages

// --- Command Line Arguments ---
const args = process.argv.slice(2);
const port = args[0];
const userId = args[1];

if (!port || !userId) {
    console.error("Error: Port and User ID must be provided as command-line arguments.");
    console.error("Usage: node server.js <PORT> <USER_ID>");
    process.exit(1);
}

const authDir = `auth_info_${userId}`;

// --- Baileys Connection Logic ---
async function connectToWhatsApp() {
    // useMultiFileAuthState will use the directory to store and manage auth state
    const { state, saveCreds } = await useMultiFileAuthState(authDir);

    sock = makeWASocket({
        auth: state
    });

    // Event listener for connection updates
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            console.log("QR code received, please scan:");
            qrcode.generate(qr, { small: true });
        }
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log(`Connection closed due to ${lastDisconnect.error}, reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                connectToWhatsApp();
            } else {
                console.log("Connection closed permanently. Not reconnecting.");
            }
        } else if (connection === 'open') {
            console.log(`WhatsApp connection opened for user ${userId}.`);
        }
    });

    // Event listener for credentials update
    sock.ev.on('creds.update', saveCreds);

    // Event listener for incoming messages
    sock.ev.on('messages.upsert', (m) => {
        m.messages.forEach(msg => {
            // Ignore notifications and messages from self
            if (!msg.message || msg.key.fromMe) {
                return;
            }

            console.log(`Received message from ${msg.key.remoteJid}`);

            const messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text || '';
            if (messageContent) {
                const incoming = {
                    sender: msg.key.remoteJid,
                    message: messageContent,
                    timestamp: new Date().toISOString()
                };
                incomingMessages.push(incoming);
            }
        });
    });
}


// --- Express Server ---
const app = express();
app.use(express.json());

// Endpoint to send a message
app.post('/send', async (req, res) => {
    const { recipient, message } = req.body;
    if (!recipient || !message) {
        return res.status(400).json({ error: 'Recipient and message are required.' });
    }
    if (!sock) {
        return res.status(503).json({ error: 'WhatsApp client is not ready.' });
    }

    try {
        // Ensure recipient is a valid JID
        const [result] = await sock.onWhatsApp(recipient);
        if (!result?.exists) {
           return res.status(400).json({ error: `Recipient ${recipient} is not on WhatsApp.`});
        }

        await sock.sendMessage(recipient, { text: message });
        console.log(`Sent message to ${recipient}`);
        res.status(200).json({ status: 'Message sent' });
    } catch (error) {
        console.error('Failed to send message:', error);
        res.status(500).json({ error: 'Failed to send message.' });
    }
});

// Endpoint for the Python client to poll for new messages
app.get('/messages', (req, res) => {
    res.status(200).json(incomingMessages);
    // Clear the queue after fetching
    incomingMessages = [];
});

const server = http.createServer(app);

server.listen(port, () => {
    console.log(`Express server for user ${userId} listening on port ${port}`);
    // Start the WhatsApp connection process after the server is up
    connectToWhatsApp().catch(err => console.error("Unexpected error during WhatsApp connection:", err));
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('SIGINT received, shutting down gracefully.');
    // The socket will close automatically when the process exits.
    // No need to logout or delete session data.
    server.close(() => {
        console.log('Express server closed.');
        process.exit(0);
    });
});
