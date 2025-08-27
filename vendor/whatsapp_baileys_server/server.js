const makeWASocket = require('@whiskeysockets/baileys').default;
const { DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const express = require('express');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const http = require('http');
const pino = require('pino');

// --- Globals ---
let sock;
let incomingMessages = []; // A simple in-memory queue for messages
let currentQR = null;
let connectionStatus = 'waiting'; // 'waiting', 'connecting', 'open', 'close'

// --- Globals ---
const serverStartTime = Date.now();

// --- Command Line Arguments ---
const args = process.argv.slice(2);
const port = args[0];
const userId = args[1];
const configBase64 = args[2] || '';

let vendorConfig = {};
try {
    if (configBase64) {
        const configJson = Buffer.from(configBase64, 'base64').toString('utf-8');
        vendorConfig = JSON.parse(configJson);
    }
} catch (e) {
    console.error("Error: Could not parse vendor config from command line.", e);
    // Continue with default config
}

if (!port || !userId) {
    console.error("Error: Port and User ID must be provided as command-line arguments.");
    console.error("Usage: node server.js <PORT> <USER_ID> [CONFIG_BASE64]");
    process.exit(1);
}

const authDir = `auth_info_${userId}`;

// --- Baileys Connection Logic ---
async function connectToWhatsApp() {
    // useMultiFileAuthState will use the directory to store and manage auth state
    const { state, saveCreds } = await useMultiFileAuthState(authDir);

    const logger = pino({ level: 'debug' });

    sock = makeWASocket({
        auth: state,
        logger: logger,
    });

    // Event listener for connection updates
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        connectionStatus = connection || 'waiting';

        if (qr) {
            console.log("QR code received, generating...");
            currentQR = qr;
            // We still print to console for debugging, but the API is the primary way to get it
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'open') {
            console.log(`WhatsApp connection opened for user ${userId}.`);
            currentQR = null; // QR is no longer needed
        }

        if (connection === 'close') {
            currentQR = null; // Clear QR on close
            const shouldReconnect = (lastDisconnect.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log(`Connection closed due to ${lastDisconnect.error}, reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                connectToWhatsApp();
            } else {
                console.log("Connection closed permanently. Not reconnecting.");
                // Optional: could add a specific status for 'loggedOut'
            }
        }
    });

    // Event listener for credentials update
    sock.ev.on('creds.update', saveCreds);

    // Event listener for incoming messages
    sock.ev.on('messages.upsert', (m) => {
        const processOffline = vendorConfig.process_offline_messages === true; // Default to false

        m.messages.forEach(msg => {
            // Ignore notifications and messages from self
            if (!msg.message || msg.key.fromMe) {
                return;
            }

            // Check if the message is old and should be ignored
            const messageTimestamp = (typeof msg.messageTimestamp === 'number' ? msg.messageTimestamp * 1000 : msg.messageTimestamp.toNumber() * 1000);
            if (!processOffline && messageTimestamp < serverStartTime) {
                console.log(`Ignoring offline message from ${msg.key.remoteJid} (sent before startup)`);
                return;
            }

            console.log(`Received message from ${msg.key.remoteJid}`);

            let messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text;

            // If there's no text content, create a placeholder for media or other types
            if (!messageContent) {
                const messageType = Object.keys(msg.message)[0] || 'unknown';
                messageContent = `[User sent a non-text message: ${messageType}]`;
            }

            const isGroup = msg.key.remoteJid.endsWith('@g.us');
            const sender = isGroup ? (msg.key.participant || msg.key.remoteJid) : msg.key.remoteJid;
            const group = isGroup ? { id: msg.key.remoteJid } : null;

            const incoming = {
                sender: sender,
                message: messageContent,
                timestamp: new Date().toISOString(),
                group: group
            };
            incomingMessages.push(incoming);
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
        // Only check if the JID exists if it's NOT a group
        if (!recipient.endsWith('@g.us')) {
            const [result] = await sock.onWhatsApp(recipient);
            if (!result?.exists) {
               return res.status(400).json({ error: `Recipient ${recipient} is not on WhatsApp.`});
            }
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

// Endpoint to get the current connection status and QR code
app.get('/status', (req, res) => {
    if (connectionStatus === 'open') {
        return res.status(200).json({ status: 'connected' });
    }
    if (currentQR) {
        // Instead of just 'qr', we can call it 'linking' to be more descriptive
        return res.status(200).json({ status: 'linking', qr: currentQR });
    }
    // For 'connecting', 'close', etc.
    return res.status(200).json({ status: connectionStatus });
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
