const { Boom } = require('@hapi/boom');
const express = require('express');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const fs = require('fs');
const http = require('http');
const pino = require('pino');
const path = require('path');

// --- Globals ---
const sessions = {}; // Holds all active user sessions, keyed by userId
const serverStartTime = Date.now();

// --- Command Line Arguments ---
const args = process.argv.slice(2);
const port = args[0] || 9000; // Default to port 9000 if not provided

// --- Baileys Connection Logic ---
async function connectToWhatsApp(userId, vendorConfig) {
    if (sessions[userId] && sessions[userId].sock) {
        console.log(`[${userId}] Session already exists. Re-initializing.`);
        // You might want to disconnect the old socket first
        try {
            await sessions[userId].sock.logout();
        } catch (e) {
            console.log(`[${userId}] Old socket logout failed, probably already disconnected.`);
        }
    }

    console.log(`[${userId}] Starting new session.`);
    const { default: makeWASocket, useMultiFileAuthState } = await import('@whiskeysockets/baileys');

    const authDir = path.resolve('running_sessions', userId, 'auth_info');
    const { state, saveCreds } = await useMultiFileAuthState(authDir);

    const logger = pino({ level: 'debug' });

    const sock = makeWASocket({
        auth: state,
        logger: logger,
        syncFullHistory: vendorConfig.sync_full_history === true,
        printQRInTerminal: false, // We handle QR code generation manually
    });

    // Store session data
    sessions[userId] = {
        sock: sock,
        incomingMessages: [],
        currentQR: null,
        connectionStatus: 'connecting',
        contactsCache: {},
        vendorConfig: vendorConfig,
    };

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        const session = sessions[userId];
        if (!session) return;

        session.connectionStatus = connection;

        if (connection === 'open') {
            console.log(`[${userId}] WhatsApp connection opened.`);
            session.currentQR = null;
        }

        if (qr) {
            console.log(`[${userId}] QR code received, generating data URL...`);
            QRCode.toDataURL(qr, (err, url) => {
                if (err) {
                    console.error(`[${userId}] Error generating QR data URL:`, err);
                    return;
                }
                session.currentQR = url;
            });
        }

        if (connection === 'close') {
            session.currentQR = null;
            const statusCode = (lastDisconnect.error instanceof Boom) ? lastDisconnect.error.output.statusCode : 500;
            if (statusCode === 401 || statusCode === 428) {
                console.log(`[${userId}] Connection closed due to invalid session. Deleting auth info and re-initializing.`);
                fs.rmSync(authDir, { recursive: true, force: true });
                // Re-initialize the connection for this user
                connectToWhatsApp(userId, vendorConfig);
            } else if (statusCode !== 440) { // 440 is logout, which is expected
                 console.log(`[${userId}] Connection closed due to:`, lastDisconnect.error, `... Attempting to reconnect.`);
                 connectToWhatsApp(userId, vendorConfig);
            } else {
                 console.log(`[${userId}] Connection closed, user logged out.`);
            }
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('contacts.update', (updates) => {
        const session = sessions[userId];
        if (!session) return;
        for (const contact of updates) {
            if (contact.id) {
                session.contactsCache[contact.id] = contact;
            }
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        const session = sessions[userId];
        if (!session) return;

        const processOffline = session.vendorConfig.process_offline_messages === true;
        const allowGroups = session.vendorConfig.allow_group_messages === true;

        const newMessagesPromises = m.messages.map(async (msg) => {
            if (!msg.message || msg.key.fromMe) return null;

            const isGroup = msg.key.remoteJid.endsWith('@g.us');
            if (isGroup && !allowGroups) return null;

            const messageTimestamp = (typeof msg.messageTimestamp === 'number' ? msg.messageTimestamp * 1000 : msg.messageTimestamp.toNumber() * 1000);
            if (!processOffline && messageTimestamp < serverStartTime) return null;

            let messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text;
            if (!messageContent) {
                const messageType = Object.keys(msg.message)[0] || 'unknown';
                messageContent = `[User sent a non-text message: ${messageType}]`;
            }

            const senderId = isGroup ? (msg.participant || msg.key.participant) : msg.key.remoteJid;
            const senderName = msg.pushName || session.contactsCache[senderId]?.name || null;

            let groupInfo = null;
            if (isGroup) {
                try {
                    const metadata = await sock.groupMetadata(msg.key.remoteJid);
                    groupInfo = { id: msg.key.remoteJid, name: metadata.subject };
                } catch (e) {
                    groupInfo = { id: msg.key.remoteJid, name: null };
                }
            }

            return {
                sender: senderId,
                display_name: senderName,
                message: messageContent,
                timestamp: new Date().toISOString(),
                group: groupInfo
            };
        });

        const newMessages = (await Promise.all(newMessagesPromises)).filter(Boolean);
        if (newMessages.length > 0) {
            session.incomingMessages.push(...newMessages);
        }
    });
}

// --- Express Server ---
const app = express();
app.use(express.json());

// Endpoint to initialize a new session for a user
app.post('/initialize', async (req, res) => {
    const { userId, config } = req.body;
    if (!userId || !config) {
        return res.status(400).json({ error: 'userId and config are required.' });
    }

    try {
        await connectToWhatsApp(userId, config);
        res.status(200).json({ status: 'Session initialization started.' });
    } catch (error) {
        console.error(`[${userId}] Failed to initialize session:`, error);
        res.status(500).json({ error: 'Failed to initialize session.' });
    }
});

// Endpoint to send a message for a specific user
app.post('/sessions/:userId/send', async (req, res) => {
    const { userId } = req.params;
    const { recipient, message } = req.body;
    const session = sessions[userId];

    if (!session || !session.sock) {
        return res.status(404).json({ error: 'Session not found or not ready.' });
    }
    if (!recipient || !message) {
        return res.status(400).json({ error: 'Recipient and message are required.' });
    }

    try {
        if (!recipient.endsWith('@g.us')) {
            const [result] = await session.sock.onWhatsApp(recipient);
            if (!result?.exists) {
                return res.status(400).json({ error: `Recipient ${recipient} is not on WhatsApp.` });
            }
        }
        await session.sock.sendMessage(recipient, { text: message });
        res.status(200).json({ status: 'Message sent' });
    } catch (error) {
        console.error(`[${userId}] Failed to send message:`, error);
        res.status(500).json({ error: 'Failed to send message.' });
    }
});

// Endpoint to poll for messages for a specific user
app.get('/sessions/:userId/messages', (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ error: 'Session not found.' });
    }

    res.status(200).json(session.incomingMessages);
    session.incomingMessages = []; // Clear queue after fetching
});

// Endpoint to get status for a specific user
app.get('/sessions/:userId/status', (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ status: 'disconnected', message: 'Session not found.' });
    }

    if (session.currentQR) {
        return res.status(200).json({ status: 'linking', qr: session.currentQR });
    }

    // Translate the internal 'open' status to 'connected' for the API
    const apiStatus = session.connectionStatus === 'open' ? 'connected' : session.connectionStatus;

    return res.status(200).json({ status: apiStatus || 'initializing' });
});

// Endpoint to delete/logout a session
app.delete('/sessions/:userId', async (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ error: 'Session not found.' });
    }

    try {
        console.log(`[${userId}] Logging out...`);
        await session.sock.logout();
        console.log(`[${userId}] Logout successful.`);
    } catch (error) {
        console.error(`[${userId}] Error during logout:`, error);
        // Don't return, still try to clean up
    } finally {
        // Clean up session object and auth files
        const authDir = path.resolve('running_sessions', userId, 'auth_info');
        if (fs.existsSync(authDir)) {
            fs.rmSync(authDir, { recursive: true, force: true });
            console.log(`[${userId}] Auth directory deleted.`);
        }
        delete sessions[userId];
        console.log(`[${userId}] Session object deleted.`);
    }

    res.status(200).json({ status: 'Session deleted successfully.' });
});


const server = http.createServer(app);
server.listen(port, () => {
    console.log(`WhatsApp Baileys multi-user server listening on port ${port}`);
    // The server is now ready to accept /initialize requests.
});

process.on('SIGINT', () => {
    console.log('SIGINT received, shutting down all sessions.');
    Object.keys(sessions).forEach(userId => {
        const session = sessions[userId];
        if (session && session.sock) {
            session.sock.end();
        }
    });
    server.close(() => {
        console.log('Express server closed.');
        process.exit(0);
    });
});
