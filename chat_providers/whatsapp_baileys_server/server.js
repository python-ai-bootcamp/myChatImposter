const { Boom } = require('@hapi/boom');
const express = require('express');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const fs = require('fs');
const http = require('http');
const pino = require('pino');

// --- Globals ---
const sessions = {}; // Store all active WhatsApp sessions, keyed by user_id
const serverStartTime = Date.now();

// --- Command Line Arguments ---
const args = process.argv.slice(2);
const port = args[0];

if (!port) {
    console.error("Error: Port must be provided as a command-line argument.");
    console.error("Usage: node server.js <PORT>");
    process.exit(1);
}

// --- Baileys Connection Logic ---
async function initializeWhatsAppSession(userId, vendorConfig = {}) {
    console.log(`Initializing WhatsApp session for user: ${userId}`);

    // Ensure the sessions directory exists to store auth info
    const sessionsDir = 'running_sessions';
    if (!fs.existsSync(sessionsDir)) {
        fs.mkdirSync(sessionsDir);
    }
    const authDir = `${sessionsDir}/auth_info_${userId}`;

    const { default: makeWASocket, useMultiFileAuthState } = await import('@whiskeysockets/baileys');
    const { state, saveCreds } = await useMultiFileAuthState(authDir);
    const logger = pino({ level: 'debug' });

    const sock = makeWASocket({
        auth: state,
        logger: logger,
        syncFullHistory: true,
    });

    // Store the session object
    sessions[userId] = {
        sock: sock,
        qr: null,
        status: 'initializing',
        messages: [],
        contacts: {},
        config: vendorConfig,
    };

    // --- Event Listeners for this session ---
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        const session = sessions[userId];

        if (connection === 'open') {
            session.status = 'connected';
            session.qr = null; // QR is no longer needed
            console.log(`WhatsApp connection opened for user ${userId}.`);
        } else if (connection) {
            session.status = connection;
        }

        if (qr) {
            console.log(`QR code received for ${userId}, generating data URL...`);
            qrcodeTerminal.generate(qr, { small: true });
            QRCode.toDataURL(qr, (err, url) => {
                if (err) {
                    console.error(`Error generating QR data URL for ${userId}:`, err);
                    return;
                }
                session.qr = url;
                session.status = 'linking';
            });
        }

        if (connection === 'close') {
            session.qr = null;
            const statusCode = (lastDisconnect.error instanceof Boom) ? lastDisconnect.error.output.statusCode : 500;

            if (statusCode === 401) {
                console.log(`Connection closed for ${userId} due to Unauthorized error. Deleting session data.`);
                if (fs.existsSync(authDir)) {
                    fs.rmSync(authDir, { recursive: true, force: true });
                }
                // The session will be removed from the sessions object later, in the /session DELETE endpoint
            }
            console.log(`Connection closed for ${userId} due to:`, lastDisconnect.error);
            // We don't automatically reconnect here anymore. The client (Python) will decide when to re-initiate.
            session.status = 'close';
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('contacts.update', (updates) => {
        for (const contact of updates) {
            if (contact.id) {
                sessions[userId].contacts[contact.id] = contact;
            }
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        const session = sessions[userId];
        if (!session) return;

        const processOffline = session.config.process_offline_messages === true;
        const allowGroups = session.config.allow_group_messages === true;

        const newMessagesPromises = m.messages.map(async (msg) => {
            if (!msg.message || msg.key.fromMe) return null;

            const isGroup = msg.key.remoteJid.endsWith('@g.us');
            if (isGroup && !allowGroups) return null;

            const messageTimestamp = (typeof msg.messageTimestamp === 'number' ? msg.messageTimestamp * 1000 : msg.messageTimestamp.toNumber() * 1000);
            if (!processOffline && messageTimestamp < serverStartTime) {
                return null;
            }

            let messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text;
            if (!messageContent) {
                const messageType = Object.keys(msg.message)[0] || 'unknown';
                messageContent = `[User sent a non-text message: ${messageType}]`;
            }

            const senderId = isGroup ? (msg.participant_pn || msg.key.participant || msg.key.remoteJid) : msg.key.remoteJid;
            const cachedContact = session.contacts[senderId];
            const senderName = msg.notify || msg.pushName || cachedContact?.name || cachedContact?.notify || null;

            let groupInfo = null;
            if (isGroup) {
                try {
                    const metadata = await sock.groupMetadata(msg.key.remoteJid);
                    groupInfo = { id: msg.key.remoteJid, name: metadata.subject };
                } catch (e) {
                    console.error(`Could not fetch group metadata for ${msg.key.remoteJid}:`, e);
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
            session.messages.push(...newMessages);
        }
    });

    return sessions[userId];
}

// --- Express Server ---
const app = express();
app.use(express.json());

// --- Session Management Endpoints ---

// Create a new session
app.post('/sessions', async (req, res) => {
    const { userId, config } = req.body;
    if (!userId) {
        return res.status(400).json({ error: 'userId is required.' });
    }
    if (sessions[userId]) {
        return res.status(409).json({ error: `Session for user ${userId} already exists.` });
    }

    try {
        await initializeWhatsAppSession(userId, config);
        console.log(`Session created for user ${userId}`);
        res.status(201).json({ status: 'Session created', userId: userId });
    } catch (error) {
        console.error(`Failed to initialize session for ${userId}:`, error);
        res.status(500).json({ error: 'Failed to initialize session.' });
    }
});

// Delete a session
app.delete('/sessions/:userId', async (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ error: `Session for user ${userId} not found.` });
    }

    try {
        // Request a logout from the WhatsApp servers
        await session.sock.logout();
    } catch (e) {
        console.warn(`Could not cleanly logout for user ${userId}, continuing with shutdown. Error: ${e}`);
    } finally {
        // Ensure the socket connection is closed
        if (session.sock && typeof session.sock.end === 'function') {
            session.sock.end();
        }

        // Remove the session from our active list
        delete sessions[userId];
        console.log(`Session deleted for user ${userId}`);

        // Optionally, you might want to clean up the auth directory
        const authDir = `running_sessions/auth_info_${userId}`;
        if (fs.existsSync(authDir)) {
            fs.rmSync(authDir, { recursive: true, force: true });
            console.log(`Authentication directory cleaned for ${userId}`);
        }

        res.status(200).json({ status: 'Session deleted', userId: userId });
    }
});


// --- Messaging Endpoints ---

// Send a message using a specific session
app.post('/sessions/:userId/send', async (req, res) => {
    const { userId } = req.params;
    const { recipient, message } = req.body;
    const session = sessions[userId];

    if (!session || !session.sock) {
        return res.status(404).json({ error: 'WhatsApp client is not ready or session not found.' });
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
        console.log(`Sent message to ${recipient} from user ${userId}`);
        res.status(200).json({ status: 'Message sent' });
    } catch (error) {
        console.error(`Failed to send message from ${userId}:`, error);
        res.status(500).json({ error: 'Failed to send message.' });
    }
});

// Poll for new messages for a specific session
app.get('/sessions/:userId/messages', (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ error: `Session for user ${userId} not found.` });
    }

    res.status(200).json(session.messages);
    // Clear the message queue for this session
    session.messages = [];
});

// Get the status of a specific session
app.get('/sessions/:userId/status', (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ status: 'not_found', message: `No session found for user ${userId}.` });
    }

    if (session.status === 'linking' && session.qr) {
        return res.status(200).json({ status: 'linking', qr: session.qr });
    }

    return res.status(200).json({ status: session.status });
});

// --- Server Startup ---
const server = http.createServer(app);

server.listen(port, () => {
    console.log(`Multi-session Express server listening on port ${port}`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('SIGINT received, shutting down all sessions gracefully.');
    const userIds = Object.keys(sessions);
    for (const userId of userIds) {
        const session = sessions[userId];
        if (session && session.sock) {
            try {
                // We don't need to logout as the session will be invalid on next startup anyway
                // and this can cause delays. Just closing the connection is faster.
                session.sock.end();
            } catch (e) {
                console.warn(`Error while closing socket for user ${userId}:`, e);
            }
        }
    }
    server.close(() => {
        console.log('Express server closed.');
        process.exit(0);
    });
});
