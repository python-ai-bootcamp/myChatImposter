const makeWASocket = require('@whiskeysockets/baileys').default;
const { DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
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
        syncFullHistory: true,
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

            const statusCode = (lastDisconnect.error instanceof Boom) ? lastDisconnect.error.output.statusCode : 500;

            // if the error is a 401 (Unauthorized), it means the session is invalid.
            // we need to delete the auth directory to force a new QR code scan.
            if (statusCode === 401) {
                console.log("Connection closed due to Unauthorized error. Deleting session and restarting...");
                // The auth directory is named after the user ID
                if (fs.existsSync(authDir)) {
                    fs.rmSync(authDir, { recursive: true, force: true });
                }
            }

            // Always try to reconnect on any disconnection.
            console.log(`Connection closed due to:`, lastDisconnect.error, `... Attempting to reconnect.`);
            connectToWhatsApp();
        }
    });

    // Event listener for credentials update
    sock.ev.on('creds.update', saveCreds);

    // Event listener for incoming messages
    sock.ev.on('messages.upsert', async (m) => { // Make it async
        const processOffline = vendorConfig.process_offline_messages === true; // Default to false
        const allowGroups = vendorConfig.allow_group_messages === true; // Default to false

        const newMessagesPromises = m.messages.map(async (msg) => { // Use map with async callback
            // Ignore notifications and messages from self
            if (!msg.message || msg.key.fromMe) {
                return null; // Return null for messages to be filtered out
            }

            const isGroup = msg.key.remoteJid.endsWith('@g.us');
            if (isGroup && !allowGroups) {
                return null;
            }

            // Check if the message is old and should be ignored
            const messageTimestamp = (typeof msg.messageTimestamp === 'number' ? msg.messageTimestamp * 1000 : msg.messageTimestamp.toNumber() * 1000);
            if (!processOffline && messageTimestamp < serverStartTime) {
                console.log(`Ignoring offline message from ${msg.key.remoteJid} (sent before startup)`);
                return null;
            }

            console.log(`Received message from ${msg.key.remoteJid}`);

            let messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text;

            if (!messageContent) {
                const messageType = Object.keys(msg.message)[0] || 'unknown';
                messageContent = `[User sent a non-text message: ${messageType}]`;
            }

            const senderId = isGroup ? (msg.key.participant || msg.key.remoteJid) : msg.key.remoteJid;
            const senderName = msg.notify || msg.pushName || null; // Get sender's name from notify or pushName

            let groupInfo = null;
            if (isGroup) {
                try {
                    // Caching group metadata would be a good optimization, but for now, let's fetch it every time.
                    const metadata = await sock.groupMetadata(msg.key.remoteJid);
                    groupInfo = { id: msg.key.remoteJid, name: metadata.subject };
                } catch (e) {
                    console.error(`Could not fetch group metadata for ${msg.key.remoteJid}:`, e);
                    groupInfo = { id: msg.key.remoteJid, name: null }; // Fallback
                }
            }

            const incoming = {
                sender: senderId,
                display_name: senderName, // Add display_name to the payload
                message: messageContent,
                timestamp: new Date().toISOString(),
                group: groupInfo
            };
            return incoming;
        });

        const newMessages = (await Promise.all(newMessagesPromises)).filter(Boolean); // Await all promises and filter out nulls

        if (newMessages.length > 0) {
            incomingMessages.push(...newMessages);
        }
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
