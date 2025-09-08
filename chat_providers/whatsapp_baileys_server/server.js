const { Boom } = require('@hapi/boom');

// --- Global Error Handlers ---
process.on('uncaughtException', (err, origin) => {
  console.error(`\n\n--- UNCAUGHT EXCEPTION ---`);
  console.error(`Caught exception: ${err}`);
  console.error(`Exception origin: ${origin}`);
  console.error(`Stack: ${err.stack}`);
  console.error(`--- END UNCAUGHT EXCEPTION ---`);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('\n\n--- UNHANDLED REJECTION ---');
  console.error('Unhandled Rejection at:', promise);
  console.error('Reason:', reason);
  console.error('--- END UNHANDLED REJECTION ---');
});

const express = require('express');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const fs = require('fs');
const http = require('http');
const { WebSocketServer } = require('ws');
const pino = require('pino');
const path = require('path');
const { MongoClient } = require('mongodb');
const {
    default: makeWASocket,
    DisconnectReason,
    jidNormalizedUser,
    initAuthCreds,
    proto
} = require('@whiskeysockets/baileys');

// --- Globals ---
const sessions = {}; // Holds all active user sessions, keyed by userId
const wsConnections = {}; // Holds all active WebSocket connections, keyed by userId
const serverStartTime = Date.now();
let baileysSessionsCollection;

// --- Command Line Arguments ---
const args = process.argv.slice(2);
const port = args[0] || 9000; // Default to port 9000 if not provided

// --- MongoDB Auth State Logic ---
const useMongoDBAuthState = async (userId, collection) => {
    const reviveBuffers = (key, value) => {
        if (value && typeof value === 'object' && value.type === 'Buffer' && Array.isArray(value.data)) {
            return Buffer.from(value.data, 'base64');
        }
        return value;
    };

    const serializeBuffers = (key, value) => {
        if (value instanceof Buffer) {
            return { type: 'Buffer', data: value.toString('base64') };
        }
        return value;
    };

    const writeData = (key, data) => {
        const jsonData = JSON.stringify(data, serializeBuffers);
        return collection.updateOne({ _id: key }, { $set: { value: jsonData } }, { upsert: true });
    };

    const readData = async (key) => {
        const doc = await collection.findOne({ _id: key });
        if (doc?.value) {
            return JSON.parse(doc.value, reviveBuffers);
        }
        return null;
    };

    const removeData = async (key) => {
        try {
            await collection.deleteOne({ _id: key });
        } catch (error) {
            // It's okay if the key doesn't exist
        }
    };

    const credsKey = `${userId}-creds`;
    const creds = (await readData(credsKey)) || initAuthCreds();

    return {
        state: {
            creds,
            keys: {
                get: async (type, ids) => {
                    const data = {};
                    await Promise.all(
                        ids.map(async id => {
                            const value = await readData(`${userId}-${type}-${id}`);
                            if (value) {
                                data[id] = value;
                            }
                        })
                    );
                    return data;
                },
                set: async (data) => {
                    const promises = [];
                    for (const type in data) {
                        for (const id in data[type]) {
                            const value = data[type][id];
                            promises.push(writeData(`${userId}-${type}-${id}`, value));
                        }
                    }
                    await Promise.all(promises);
                },
                remove: async (type, ids) => {
                    const promises = [];
                    for (const id of ids) {
                        promises.push(removeData(`${userId}-${type}-${id}`));
                    }
                    await Promise.all(promises);
                }
            },
        },
        saveCreds: () => {
            return writeData(credsKey, creds);
        },
    };
};


// --- Baileys Connection Logic ---
async function connectToWhatsApp(userId, vendorConfig) {
    if (sessions[userId] && sessions[userId].sock) {
        console.log(`[${userId}] Session already exists. Re-initializing.`);
        try {
            // End the old socket connection without logging out
            sessions[userId].sock.end(undefined);
            console.log(`[${userId}] Old socket connection ended.`);

            // Close the WebSocket connection to force the client to reconnect
            wsConnections[userId]?.close();
            console.log(`[${userId}] Old WebSocket connection closed.`);

        } catch (e) {
            console.log(`[${userId}] Old socket cleanup failed:`, e);
        }
        delete sessions[userId];
    }

    console.log(`[${userId}] Starting new session.`);

    const { state, saveCreds } = await useMongoDBAuthState(userId, baileysSessionsCollection);

    const logger = pino({ level: 'debug' });

    const sock = makeWASocket({
        auth: state,
        logger: logger,
        syncFullHistory: vendorConfig.sync_full_history === true,
        printQRInTerminal: false, // We handle QR code generation manually
    });

    sessions[userId] = {
        sock: sock,
        currentQR: null,
        connectionStatus: 'connecting',
        contactsCache: {},
        vendorConfig: vendorConfig,
        retryCount: 0,
    };

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        const session = sessions[userId];
        if (!session) return;

        session.connectionStatus = connection;

        if (connection === 'open') {
            console.log(`[${userId}] WhatsApp connection opened.`);
            session.currentQR = null;
            session.retryCount = 0; // Reset retry count
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
            if (statusCode === DisconnectReason.loggedOut || statusCode === DisconnectReason.connectionReplaced) {
                console.log(`[${userId}] Connection closed, user logged out or session replaced.`);
                wsConnections[userId]?.close();
                delete sessions[userId];
            } else if (statusCode === DisconnectReason.badSession) {
                console.log(`[${userId}] Connection closed due to invalid session. Deleting auth info and re-initializing.`);
                baileysSessionsCollection.deleteMany({ _id: { $regex: `^${userId}-` } }).then(() => {
                    connectToWhatsApp(userId, vendorConfig);
                });
            } else {
                session.retryCount = (session.retryCount || 0) + 1;
                console.log(`[${userId}] Connection closed due to:`, lastDisconnect.error, `(retry #${session.retryCount})`);

                if (session.retryCount >= 3) {
                    console.log(`[${userId}] Max retries reached. Treating as a bad session.`);
                    baileysSessionsCollection.deleteMany({ _id: { $regex: `^${userId}-` } }).then(() => {
                        console.log(`[${userId}] Auth info deleted. Session will be re-initialized for QR scan.`);
                        connectToWhatsApp(userId, vendorConfig);
                    });
                } else {
                    console.log(`[${userId}] Attempting to reconnect in 5s...`);
                    setTimeout(() => connectToWhatsApp(userId, vendorConfig), 5000); // Wait 5s before reconnecting
                }
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

        // If we are receiving messages, we can consider the connection open
        if (session.connectionStatus !== 'open') {
            console.log(`[${userId}] Received messages while not in 'open' state, updating status.`);
            session.connectionStatus = 'open';
        }

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
            const ws = wsConnections[userId];
            if (ws && ws.readyState === ws.OPEN) {
                ws.send(JSON.stringify(newMessages));
            } else {
                console.log(`[${userId}] WebSocket not open, cannot send messages.`);
            }
        }
    });
}

// --- Express Server ---
const app = express();
app.use(express.json());

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

app.get('/sessions/:userId/status', (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];
    if (!session) {
        return res.status(404).json({ status: 'disconnected', message: 'Session not found.' });
    }
    if (session.currentQR) {
        return res.status(200).json({ status: 'linking', qr: session.currentQR });
    }
    const apiStatus = session.connectionStatus === 'open' ? 'connected' : session.connectionStatus;
    return res.status(200).json({ status: apiStatus || 'initializing' });
});

app.delete('/sessions/:userId', async (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];

    if (!session) {
        return res.status(404).json({ error: 'Session not found.' });
    }

    try {
        console.log(`[${userId}] Logging out...`);
        await session.sock.logout();
    } catch (error) {
        console.error(`[${userId}] Error during logout:`, error);
    } finally {
        try {
            const deleteResult = await baileysSessionsCollection.deleteMany({ _id: { $regex: `^${userId}-` } });
            console.log(`[${userId}] Deleted ${deleteResult.deletedCount} auth entries from MongoDB.`);
        } catch (dbError) {
            console.error(`[${userId}] Error deleting auth data from MongoDB:`, dbError);
        }
        delete sessions[userId];
        console.log(`[${userId}] Session object deleted.`);
    }

    res.status(200).json({ status: 'Session deleted successfully.' });
});

async function startServer() {
    const mongoUrl = process.env.MONGODB_URL || 'mongodb://mongodb:27017';
    let mongoClient;
    try {
        console.log(`Connecting to MongoDB at ${mongoUrl}`);
        mongoClient = new MongoClient(mongoUrl);
        await mongoClient.connect();
        const db = mongoClient.db('chat_manager');
        baileysSessionsCollection = db.collection('baileys_sessions');
        console.log('Successfully connected to MongoDB.');

        const server = http.createServer(app);
        const wss = new WebSocketServer({ server });

        wss.on('connection', (ws, req) => {
            const url = new URL(req.url, `http://${req.headers.host}`);
            const userId = url.pathname.split('/')[1];

            if (!userId || !sessions[userId]) {
                console.log(`[WebSocket] Connection rejected: No session for userId '${userId}'`);
                ws.close();
                return;
            }

            console.log(`[WebSocket] Client connected for userId: ${userId}`);
            wsConnections[userId] = ws;

            ws.on('close', () => {
                console.log(`[WebSocket] Client disconnected for userId: ${userId}`);
                delete wsConnections[userId];
            });

            ws.on('error', (error) => {
                console.error(`[WebSocket] Error for userId ${userId}:`, error);
            });
        });

        server.listen(port, () => {
            console.log(`WhatsApp Baileys multi-user server listening on port ${port}`);
        });

        process.on('SIGINT', async () => {
            console.log('SIGINT received, shutting down all sessions.');
            for (const userId in sessions) {
                const session = sessions[userId];
                if (session && session.sock) {
                    session.sock.end(new Error('Server shutting down'));
                }
            }
            await mongoClient.close();
            console.log('MongoDB connection closed.');
            server.close(() => {
                console.log('Express server closed.');
                process.exit(0);
            });
        });

    } catch (e) {
        console.error("Failed to connect to MongoDB", e);
        process.exit(1);
    }
}

startServer();
