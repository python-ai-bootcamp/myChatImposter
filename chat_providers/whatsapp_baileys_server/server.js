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
    proto,
    fetchLatestBaileysVersion,
} = require('@whiskeysockets/baileys');

// --- Globals ---
const sessions = {}; // Holds all active user sessions, keyed by userId
const wsConnections = {}; // Holds all active WebSocket connections, keyed by userId
const serverStartTime = Date.now();
const DEFAULT_BROWSER = ['Ubuntu', 'Chrome', '22.04.4'];
const MAX_HTTP405_RETRIES = 3;
const HTTP405_WINDOW_MS = 30 * 1000;
const RETRY_DELAY_MS = 5000;
let baileysSessionsCollection;

const createHttp405Tracker = () => ({
    count: 0,
    firstTimestamp: 0,
    locations: [],
});

const resetHttp405Tracker = (session) => {
    session.http405Tracker = createHttp405Tracker();
};

const trackHttp405 = (session, lastDisconnect) => {
    const now = Date.now();
    if (!session.http405Tracker) {
        resetHttp405Tracker(session);
    }
    const tracker = session.http405Tracker;
    const location = lastDisconnect?.error?.data?.location || lastDisconnect?.error?.data?.reason || 'unknown';

    if (!tracker.firstTimestamp || now - tracker.firstTimestamp > HTTP405_WINDOW_MS) {
        tracker.firstTimestamp = now;
        tracker.count = 1;
        tracker.locations = [location];
    } else {
        tracker.count += 1;
        tracker.locations.push(location);
    }
};

const shouldForceRelink = (statusCode, session) => {
    if (statusCode !== 405) return false;
    const tracker = session.http405Tracker;
    if (!tracker || tracker.count < MAX_HTTP405_RETRIES) {
        return false;
    }
    const withinWindow = tracker.firstTimestamp && (Date.now() - tracker.firstTimestamp) <= HTTP405_WINDOW_MS;
    return withinWindow && tracker.count >= MAX_HTTP405_RETRIES;
};

const logPersistent405 = (userId, session) => {
    const tracker = session.http405Tracker;
    if (!tracker) return;
    const duration = tracker.firstTimestamp ? (Date.now() - tracker.firstTimestamp) : 0;
    const locations = tracker.locations.length ? tracker.locations.join(', ') : 'unknown';
    console.log(`[${userId}] Persistent 405 errors: ${tracker.count} hits over ${duration}ms. POPs: ${locations}`);
};

const addIdentifierVariant = (set, value) => {
    if (!value || typeof value !== 'string') {
        return;
    }
    set.add(value);
    if (value.includes('@')) {
        const bare = value.split('@')[0];
        if (bare) {
            set.add(bare);
        }
    }
    try {
        const normalized = jidNormalizedUser(value);
        if (normalized) {
            set.add(normalized);
        }
    } catch (err) {
        // ignore normalization errors
    }
};

const collectSenderIdentifiers = (msg, primaryIdentifier) => {
    const identifiers = new Set();
    addIdentifierVariant(identifiers, primaryIdentifier);
    const potentialValues = [
        msg?.key?.remoteJid,
        msg?.messageKey?.remoteJid,
        msg?.participant,
        msg?.key?.participant,
        msg?.messageKey?.participant,
        msg?.key?.senderJid,
        msg?.messageKey?.senderJid,
        msg?.messageKey?.senderPn,
    ];
    potentialValues.forEach((value) => addIdentifierVariant(identifiers, value));
    return Array.from(identifiers).filter(Boolean);
};





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
let cachedWaVersion;
let cachedWaVersionLogged = false;

async function getLatestWaVersion() {
    if (!cachedWaVersion) {
        const { version, isLatest } = await fetchLatestBaileysVersion();
        cachedWaVersion = version;
        console.log(`[Baileys] Using WhatsApp Web version ${version.join('.')}${isLatest ? '' : ' (not latest - update Baileys!)'}`);
    }
    return cachedWaVersion;
}

async function connectToWhatsApp(userId, vendorConfig) {
    const waVersion = await getLatestWaVersion();


    if (sessions[userId] && sessions[userId].sock) {
        console.log(`[${userId}] Session already exists. Re-initializing.`);
        try {
            // End the old socket connection without logging out
            await sessions[userId].sock.end(undefined);
            console.log(`[${userId}] Old socket connection ended.`);

            // Close the WebSocket connection to force the client to reconnect
            wsConnections[userId]?.close();
            console.log(`[${userId}] Old WebSocket connection closed.`);

        } catch (e) {
            console.log(`[${userId}] Old socket cleanup failed:`, e);
        }
        // We don't delete the session object. We will re-use and update it.
        // This prevents a race condition where the client reconnects before the new session is ready.
    }

    console.log(`[${userId}] Starting new session connection...`);

    const { state, saveCreds } = await useMongoDBAuthState(userId, baileysSessionsCollection);

    const logger = pino({ level: 'debug' });

    const sock = makeWASocket({
        auth: state,
        logger: logger,
        version: waVersion,
        browser: DEFAULT_BROWSER,
        syncFullHistory: vendorConfig.sync_full_history === true,
        printQRInTerminal: false, // We handle QR code generation manually
    });


    // If a session object already exists, update it. Otherwise, create a new one.
    // This preserves the object reference and prevents race conditions.
    if (sessions[userId]) {
        console.log(`[${userId}] Updating existing session object.`);
        sessions[userId].sock = sock;
        sessions[userId].currentQR = null;
        sessions[userId].connectionStatus = 'connecting';
        sessions[userId].retryCount = 0;
        sessions[userId].lidCache = {}; // Also reset cache on reconnect
        sessions[userId].pushNameCache = {}; // Reset pushName cache
        resetHttp405Tracker(sessions[userId]);
    } else {
        console.log(`[${userId}] Creating new session object.`);
        sessions[userId] = {
            sock: sock,
            currentQR: null,
            connectionStatus: 'connecting',
            contactsCache: {},
            lidCache: {},
            pushNameCache: {},
            vendorConfig: vendorConfig,
            retryCount: 0,
            http405Tracker: createHttp405Tracker(),
        };
    }


    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        const session = sessions[userId];
        if (!session || session.isUnlinking) return;

        session.connectionStatus = connection;

        if (connection === 'open') {
            console.log(`[${userId}] WhatsApp connection opened.`);
            session.currentQR = null;
            session.retryCount = 0; // Reset retry count
            resetHttp405Tracker(session);
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

            const isPermanentDisconnection =
                statusCode === DisconnectReason.loggedOut ||
                statusCode === DisconnectReason.connectionReplaced ||
                statusCode === DisconnectReason.badSession;

            const maxRetriesReached = (session.retryCount || 0) >= 3;

            if (statusCode === DisconnectReason.restartRequired) {
                console.log(`[${userId}] Connection requires a restart. Reconnecting immediately.`);
                connectToWhatsApp(userId, vendorConfig);

            } else if (isPermanentDisconnection || shouldForceRelink(statusCode, session)) {
                if (!isPermanentDisconnection) {
                    logPersistent405(userId, session);
                }
                const reason = isPermanentDisconnection ? `permanent disconnect (code: ${statusCode})` : 'persistent 405 errors';
                console.log(`[${userId}] Connection closed permanently due to ${reason}. Cleaning up and forcing re-link.`);

                wsConnections[userId]?.close();

                baileysSessionsCollection.deleteMany({ _id: { $regex: `^${userId}-` } })
                    .then(() => {
                        console.log(`[${userId}] Auth info deleted. Re-initializing to generate new QR code.`);
                        setTimeout(() => connectToWhatsApp(userId, vendorConfig), 1000);
                    })
                    .catch(err => {
                        console.error(`[${userId}] Failed to delete auth info from DB:`, err);
                    });

            } else { // Handle other transient errors with retry logic
                session.retryCount = (session.retryCount || 0) + 1;
                if (statusCode === 405) {
                    trackHttp405(session, lastDisconnect);
                }
                console.log(`[${userId}] Connection closed transiently (code: ${statusCode}). Retry #${session.retryCount}.`);
                console.log(`[${userId}] Underlying error:`, lastDisconnect.error);
                console.log(`[${userId}] Attempting to reconnect in 5s...`);
                setTimeout(() => connectToWhatsApp(userId, vendorConfig), RETRY_DELAY_MS);
            }
        }
    });

    sock.ev.on('creds.update', async () => {
        try {
            await saveCreds();
        } catch(e) {
            console.error(`[${userId}] Error saving credentials:`, e);
        }
    });

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
        try {
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
            if (msg?.key?.senderPn) {
                console.log(`[${userId}] Normalized senderPn detected: ${msg.key.senderPn}`);
            }
            if (msg?.messageKey?.senderPn) {
                console.log(`[${userId}] messageKey senderPn present: ${msg.messageKey.senderPn}`);
            }
            console.log(`[${userId}] Raw message key info:`, {
                remoteJid: msg?.key?.remoteJid,
                senderJid: msg?.key?.senderJid,
                senderPn: msg?.key?.senderPn || msg?.messageKey?.senderPn,
                participant: msg?.participant || msg?.key?.participant,
                pushName: msg?.pushName,
                contactsCacheName: (msg?.key?.remoteJid && session.contactsCache[msg.key.remoteJid]?.name) || null,
            });
            console.log("entire msg object::\n----------", msg, "\n--------");
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
            const senderPn = msg?.key?.senderPn || msg?.messageKey?.senderPn || msg?.key?.senderJid || null;
            if (senderId && senderId.endsWith('@lid') && senderPn) {
                if (!session.lidCache) session.lidCache = {};
                session.lidCache[senderId] = senderPn;
                console.log(`[${userId}] Cached LID mapping: ${senderId} -> ${senderPn}`);
            }
            if (!senderPn && !isGroup) {
                const normalizedRemote = jidNormalizedUser?.(msg.key.remoteJid);
                if (normalizedRemote && normalizedRemote !== msg.key.remoteJid) {
                    msg.messageKey = msg.messageKey || {};
                    msg.messageKey.senderPn = normalizedRemote;
                }
            }

            // Cache the pushName whenever it's available
            if (msg.pushName) {
                session.pushNameCache[senderId] = msg.pushName;
            }
            const senderName = msg.pushName || session.pushNameCache[senderId] || session.contactsCache[senderId]?.name || null;

            let groupInfo = null;
            if (isGroup) {
                try {
                    const metadata = await sock.groupMetadata(msg.key.remoteJid);
                    console.log("entire metadata object::\n----------", metadata, "\n--------");
                    groupInfo = { id: msg.key.remoteJid, name: metadata.subject };
                    console.log("entire groupInfo object::\n----------", groupInfo, "\n--------");
                } catch (e) {
                    groupInfo = { id: msg.key.remoteJid, name: null };
                }
            }

            const alternateIdentifiers = collectSenderIdentifiers(msg, senderId);
            if (senderPn && !alternateIdentifiers.includes(senderPn)) {
                alternateIdentifiers.push(senderPn);
            }

            const participantPn = msg?.key?.participantPn;
            if (participantPn && !alternateIdentifiers.includes(participantPn)) {
                alternateIdentifiers.push(participantPn);
            }

            console.log(`[${userId}] Derived alternate identifiers:`, alternateIdentifiers);

            return {
                provider_message_id: msg.key.id,
                sender: senderId,
                display_name: senderName,
                message: messageContent,
                timestamp: new Date().toISOString(),
                group: groupInfo,
                alternate_identifiers: alternateIdentifiers,
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
        } catch (e) {
            console.error(`[${userId}] Error in messages.upsert handler:`, e);
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
    let { recipient } = req.body;
    const { message } = req.body;
    const session = sessions[userId];

    if (!session || !session.sock) {
        return res.status(404).json({ error: 'Session not found or not ready.' });
    }
    if (!recipient || !message) {
        return res.status(400).json({ error: 'Recipient and message are required.' });
    }

    try {
        if (recipient.endsWith('@lid')) {
            const cachedJid = session.lidCache && session.lidCache[recipient];
            if (cachedJid) {
                console.log(`[${userId}] Resolved LID ${recipient} -> ${cachedJid} from cache.`);
                recipient = cachedJid;
            } else {
                const normalized = recipient.replace('@lid', '@s.whatsapp.net');
                console.log(`[${userId}] WARN: No cache for LID ${recipient}. Falling back to normalization: ${normalized}`);
                recipient = normalized;
            }
        }

        if (!recipient.endsWith('@g.us') && !recipient.endsWith('@s.whatsapp.net')) {
            const [result] = await session.sock.onWhatsApp(recipient);
            if (!result?.exists) {
                return res.status(400).json({ error: `Recipient ${recipient} is not on WhatsApp.` });
            }
        }
        await session.sock.sendMessage(recipient, { text: message });
        console.log(`[${userId}] sendMessage() invoked for ${recipient}`);
        res.status(200).json({ status: 'Message sent', recipient, message });
    } catch (error) {
        const statusCode = error?.output?.statusCode || (error?.response?.status) || 500;
        const messageText = error?.response?.data || error?.message || 'Failed to send message.';
        console.error(`[${userId}] Failed to send message:`, error);
        res.status(statusCode).json({ error: messageText });
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
        session.isUnlinking = true;
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
