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
    try {
        const normalized = jidNormalizedUser(value);
        if (normalized) {
            set.add(normalized);
        }
    } catch (err) {
        // ignore normalization errors
    }
};

// Enrich identifiers with bidirectional LID/PN cache lookups
const enrichIdentifiersFromCache = (identifiersSet, lidCache) => {
    if (!lidCache || Object.keys(lidCache).length === 0) return;

    const currentIdentifiers = Array.from(identifiersSet);
    for (const id of currentIdentifiers) {
        if (id.endsWith('@lid')) {
            // Forward lookup: LID -> PN (try normalized LID too)
            const normalizedLid = jidNormalizedUser(id);
            const pn = lidCache[id] || lidCache[normalizedLid];
            if (pn) addIdentifierVariant(identifiersSet, pn);
        } else if (id.endsWith('@s.whatsapp.net')) {
            // Reverse lookup: PN -> LID
            const normalizedPn = jidNormalizedUser(id);
            const lid = Object.keys(lidCache).find(key => {
                const cached = lidCache[key];
                return cached === id || cached === normalizedPn || jidNormalizedUser(cached) === normalizedPn;
            });
            if (lid) addIdentifierVariant(identifiersSet, lid);
        }
    }
};

const collectSenderIdentifiers = (msg, primaryIdentifier, lidCache = {}) => {
    const identifiers = new Set();
    addIdentifierVariant(identifiers, primaryIdentifier);
    const isGroup = msg?.key?.remoteJid?.endsWith('@g.us');

    const potentialValues = [
        // remoteJid is the correspondent ID. Only add if not a group.
        isGroup ? null : msg?.key?.remoteJid,
        isGroup ? null : msg?.messageKey?.remoteJid,
        // participant is the sender in a group context
        msg?.participant,
        msg?.key?.participant,
        msg?.messageKey?.participant,
        msg?.key?.senderJid,
        msg?.messageKey?.senderJid,
        msg?.messageKey?.senderPn,
    ];
    potentialValues.forEach((value) => addIdentifierVariant(identifiers, value));

    // Enrich with LID cache lookups for bidirectional resolution
    enrichIdentifiersFromCache(identifiers, lidCache);

    return Array.from(identifiers).filter(Boolean);
};

const collectGroupIdentifiers = (groupInfo) => {
    if (!groupInfo) {
        return [];
    }
    const identifiers = new Set();
    addIdentifierVariant(identifiers, groupInfo.id);
    addIdentifierVariant(identifiers, groupInfo.name);
    return Array.from(identifiers).filter(Boolean);
};

// --- Contact Processing Helper ---
const processContacts = (session, userId, contacts) => {
    if (!contacts || !contacts.length) return;

    const selfId = session.sock?.user?.id ? jidNormalizedUser(session.sock.user.id) : null;
    let addedCount = 0;

    for (const contact of contacts) {
        if (contact.id) {
            session.contactsCache[contact.id] = Object.assign(session.contactsCache[contact.id] || {}, contact);

            // Also cache notify name if available as pushName
            if (contact.notify || contact.name) {
                session.pushNameCache[contact.id] = contact.notify || contact.name;
            }
            // Learn LID mapping from contact if it has lid field
            if (contact.lid && contact.id) {
                const contactPn = jidNormalizedUser(contact.id);
                const contactLid = jidNormalizedUser(contact.lid);
                if (contactPn && contactLid && contactLid.endsWith('@lid')) {
                    if (!session.lidCache) session.lidCache = {};
                    if (session.lidCache[contactLid] !== contactPn) {
                        session.lidCache[contactLid] = contactPn;
                        // Check if this is self
                        const isSelf = selfId && (contactPn === selfId || contact.id.includes(selfId.split(':')[0]));
                        if (isSelf) {
                            console.log(`[${userId}] Learned Self LID from contacts: ${contactLid} -> ${contactPn}`);
                        }
                        saveLidMapping(userId, contactLid, contactPn);
                    }
                }
            }
            addedCount++;
        }
    }
    // console.log(`[${userId}] Processed ${addedCount} contacts.`);
};

// --- Message Processing Helper ---
async function processMessage(session, userId, msg, processOffline, allowGroups) {
    if (msg?.key?.senderPn) {
        console.log(`[${userId}] Normalized senderPn detected: ${msg.key.senderPn}`);
    }
    if (msg?.messageKey?.senderPn) {
        console.log(`[${userId}] messageKey senderPn present: ${msg.messageKey.senderPn}`);
    }

    const isGroup = msg.key.remoteJid.endsWith('@g.us');
    const senderId = isGroup ? (msg.participant || msg.key.participant) : msg.key.remoteJid;
    let senderPn = msg?.key?.senderPn || msg?.messageKey?.senderPn || msg?.key?.senderJid || null;

    // Fallback: If senderPn is missing but senderId is an LID, try to find it in the cache
    if (!senderPn && senderId && senderId.endsWith('@lid')) {
        if (session.lidCache) {
            const cachedPn = session.lidCache[senderId];
            if (cachedPn) {
                // console.log(`[${userId}] Resolved missing senderPn from cache: ${senderId} -> ${cachedPn}`);
                senderPn = cachedPn;
            }
        }
    }

    // Self-Learning: Learn LID mapping when we can identify self messages
    // This triggers for fromMe messages OR when senderId matches known self identifiers
    if (session.sock?.user) {
        const selfId = jidNormalizedUser(session.sock.user.id);
        const selfLidFromSession = session.sock.user.lid ? jidNormalizedUser(session.sock.user.lid) : null;

        // Check if senderId is self (for group messages, senderId is the participant)
        const normalizedSenderId = jidNormalizedUser(senderId);
        const isSelfBySenderId = normalizedSenderId === selfId || normalizedSenderId === selfLidFromSession;

        // Also check via cache reverse lookup if we already have a mapping
        const cachedSelfLid = session.lidCache ? Object.keys(session.lidCache).find(key => session.lidCache[key] === selfId) : null;
        const isSelfByCache = cachedSelfLid && normalizedSenderId === jidNormalizedUser(cachedSelfLid);

        const isSelfMessage = msg.key.fromMe || isSelfBySenderId || isSelfByCache;

        // DEBUG: Trace why we are missing self messages
        if (msg.key.fromMe || isSelfBySenderId) {
            console.log(`[${userId}] Self msg check. fromMe: ${msg.key.fromMe}, isGroup: ${isGroup}, senderId: ${senderId}, selfId: ${selfId}, selfLid: ${selfLidFromSession}, LID Cached: ${!!cachedSelfLid}`);
        }

        if (isSelfMessage && isGroup) {
            // For group messages, learn the LID mapping from senderId (which is participant)
            if (senderId && senderId.endsWith('@lid') && selfId) {
                const normalizedLid = jidNormalizedUser(senderId);
                if (!session.lidCache) session.lidCache = {};
                if (session.lidCache[normalizedLid] !== selfId) {
                    session.lidCache[normalizedLid] = selfId;
                    console.log(`[${userId}] Learned Self LID mapping (from group): ${normalizedLid} -> ${selfId}`);
                    saveLidMapping(userId, normalizedLid, selfId);
                }
            } else {
                // console.log(`[${userId}] Skipped Self LID learning. senderId: ${senderId}, selfId: ${selfId}`);
            }
        }

        // Also try participant field for direct messages
        if (msg.key.fromMe) {
            const rawParticipant = msg.participant || msg.key.participant;
            const potentialLid = jidNormalizedUser(rawParticipant);
            if (potentialLid && selfId && potentialLid.endsWith('@lid')) {
                if (!session.lidCache) session.lidCache = {};
                if (session.lidCache[potentialLid] !== selfId) {
                    session.lidCache[potentialLid] = selfId;
                    console.log(`[${userId}] Learned Self LID mapping: ${potentialLid} -> ${selfId}`);
                    saveLidMapping(userId, potentialLid, selfId);
                }
            }
        }
    }

    // Explicitly handle "Self" identification to ensure both LID and PN are present
    // This catches cases where manual messages might only have one identifier
    if (session.sock?.user) {
        const selfId = jidNormalizedUser(session.sock.user.id);
        let selfLid = jidNormalizedUser(session.sock.user.lid);

        // Fallback 1: If LID is missing in session (e.g. fresh login), try to find it in cache via reverse lookup
        if (!selfLid && session.lidCache) {
            const cachedLid = Object.keys(session.lidCache).find(key => session.lidCache[key] === selfId);
            if (cachedLid) {
                selfLid = jidNormalizedUser(cachedLid);
            }
        }

        // Fallback 2: Check contacts cache for selfId to find LID
        if (!selfLid && session.contactsCache && session.contactsCache[selfId]) {
            const selfContact = session.contactsCache[selfId];
            if (selfContact.lid) {
                selfLid = jidNormalizedUser(selfContact.lid);
                // Persist this found mapping
                if (!session.lidCache) session.lidCache = {};
                if (session.lidCache[selfLid] !== selfId) {
                    session.lidCache[selfLid] = selfId;
                    console.log(`[${userId}] Resolved selfLid from contacts: ${selfLid} -> ${selfId}`);
                    saveLidMapping(userId, selfLid, selfId);
                }
            }
        }

        const normalizedSender = jidNormalizedUser(senderId);

        if (normalizedSender && (normalizedSender === selfId || normalizedSender === selfLid)) {
            // Sender is ME. Ensure we have both PN and LID.
            if (selfId && selfId !== senderId) {
                // Add PN to alternate identifiers later
                // Also set senderPn if it was missing
                if (!senderPn) senderPn = selfId;
            }

            // If we have both, ensure mapping is saved
            if (selfLid && selfId) {
                if (!session.lidCache) session.lidCache = {};
                if (session.lidCache[selfLid] !== selfId) {
                    session.lidCache[selfLid] = selfId;
                    console.log(`[${userId}] Self-repair: Mapped Self LID ${selfLid} -> ${selfId}`);
                    saveLidMapping(userId, selfLid, selfId);
                }
            }
        }
    }

    // Cache pushName and LID mappings from ANY message, even stubs
    const cacheKey = senderPn || senderId;
    if (msg.pushName) {
        session.pushNameCache[cacheKey] = msg.pushName;
    }
    if (senderId && senderId.endsWith('@lid') && senderPn) {
        if (!session.lidCache) session.lidCache = {};
        if (session.lidCache[senderId] !== senderPn) {
            session.lidCache[senderId] = senderPn;
            console.log(`[${userId}] New LID mapping found: ${senderId} -> ${senderPn}. Saving to DB.`);
            saveLidMapping(userId, senderId, senderPn);
        }
    }

    if (!msg.message) {
        console.log(`[${userId}] Received a stub message or an event with no message body. Type: ${msg.messageStubType}, Params: ${msg.messageStubParameters?.join(', ')}. Skipping. Full msg: ${JSON.stringify(msg)}`);
        return null;
    }

    // Filter out technical keys to find the actual content type
    const rawKeys = Object.keys(msg.message);
    const technicalKeys = ['senderKeyDistributionMessage', 'messageContextInfo', 'keepInChatMessage'];
    const contentKeys = rawKeys.filter(k => !technicalKeys.includes(k));
    const messageType = contentKeys.length > 0 ? contentKeys[0] : rawKeys[0];

    if (messageType === 'protocolMessage') {
        // console.log(`[${userId}] Skipping protocolMessage.`);
        return null;
    }
    if (contentKeys.length === 0 && messageType === 'senderKeyDistributionMessage') return null;

    if (isGroup && !allowGroups) {
        console.log(`[${userId}] Skipping group message from ${msg.key.remoteJid} (allow_group_messages=false).`);
        return null;
    }

    const messageTimestamp = (typeof msg.messageTimestamp === 'number' ? msg.messageTimestamp * 1000 : msg.messageTimestamp.toNumber() * 1000);
    if (!processOffline && messageTimestamp < serverStartTime) {
        console.log(`[${userId}] Skipping offline message from ${msg.key.remoteJid} (ts: ${messageTimestamp} < start: ${serverStartTime}).`);
        return null;
    }

    let messageContent = msg.message.conversation || msg.message.extendedTextMessage?.text;
    if (!messageContent) {
        const type = Object.keys(msg.message)[0] || 'unknown';
        messageContent = `[User sent a non-text message: ${type}]`;
    }

    if (!senderPn && !isGroup) {
        const normalizedRemote = jidNormalizedUser?.(msg.key.remoteJid);
        if (normalizedRemote && normalizedRemote !== msg.key.remoteJid) {
            msg.messageKey = msg.messageKey || {};
            msg.messageKey.senderPn = normalizedRemote;
        }
    }

    const senderName = msg.pushName || session.pushNameCache[senderId] || session.pushNameCache[senderPn] || session.contactsCache[senderId]?.name || null;

    let groupInfo = null;
    if (isGroup) {
        try {
            // Using session.sock directly might be an issue if called from outside,
            // but for this helper assume session.sock is available.
            const metadata = await session.sock.groupMetadata(msg.key.remoteJid);
            groupInfo = { id: msg.key.remoteJid, name: metadata.subject };
            groupInfo.alternate_identifiers = collectGroupIdentifiers(groupInfo);
        } catch (e) {
            groupInfo = { id: msg.key.remoteJid, name: null };
            groupInfo.alternate_identifiers = collectGroupIdentifiers(groupInfo);
        }
    }

    const alternateIdentifiers = new Set(collectSenderIdentifiers(msg, senderId, session.lidCache));
    addIdentifierVariant(alternateIdentifiers, senderPn);
    addIdentifierVariant(alternateIdentifiers, msg?.key?.participantPn);
    addIdentifierVariant(alternateIdentifiers, senderName); // Add display name

    // If sender is Self, force add both Self PN and Self LID
    if (session.sock?.user) {
        const selfId = jidNormalizedUser(session.sock.user.id);
        const selfLid = jidNormalizedUser(session.sock.user.lid);
        const normalizedSender = jidNormalizedUser(senderId);

        if (normalizedSender && (normalizedSender === selfId || normalizedSender === selfLid)) {
            addIdentifierVariant(alternateIdentifiers, selfId);
            addIdentifierVariant(alternateIdentifiers, selfLid);
        }
    }

    const finalSenderIdentifiers = Array.from(alternateIdentifiers).filter(Boolean);

    let recipientId = msg.key.remoteJid;
    if (msg.key.fromMe && recipientId.endsWith('@lid')) {
        const resolvedJid = session.lidCache && session.lidCache[recipientId];
        if (resolvedJid) {
            recipientId = resolvedJid;
        } else {
            recipientId = recipientId.replace('@lid', '@s.whatsapp.net');
        }
    }

    let actualSender = null;
    if (msg.key.fromMe) {
        const selfJid = session.sock?.user?.id;
        let selfLid = session.sock?.user?.lid;

        // Fallback: Resolve selfLid from cache if missing
        if (!selfLid) {
            const normalizedSelfJid = jidNormalizedUser(selfJid);

            // Try lidCache
            if (session.lidCache) {
                const cachedLid = Object.keys(session.lidCache).find(key => session.lidCache[key] === normalizedSelfJid);
                if (cachedLid) selfLid = cachedLid;
            }

            // Try contactsCache
            if (!selfLid && session.contactsCache && session.contactsCache[normalizedSelfJid]) {
                const selfContact = session.contactsCache[normalizedSelfJid];
                if (selfContact.lid) {
                    selfLid = jidNormalizedUser(selfContact.lid);
                    // Persist (fire and forget for this block)
                    if (session.lidCache && session.lidCache[selfLid] !== normalizedSelfJid) {
                        session.lidCache[selfLid] = normalizedSelfJid;
                        saveLidMapping(userId, selfLid, normalizedSelfJid);
                    }
                }
            }
        }

        const selfName = msg.pushName;
        const selfAlternate = new Set();
        addIdentifierVariant(selfAlternate, selfJid);
        addIdentifierVariant(selfAlternate, selfLid);
        addIdentifierVariant(selfAlternate, selfName);
        enrichIdentifiersFromCache(selfAlternate, session.lidCache);

        actualSender = {
            identifier: selfJid,
            display_name: selfName,
            alternate_identifiers: Array.from(selfAlternate).filter(Boolean),
        };
    }

    return {
        provider_message_id: msg.key.id,
        sender: senderId,
        display_name: senderName,
        message: messageContent,
        timestamp: new Date().toISOString(),
        group: groupInfo,
        alternate_identifiers: finalSenderIdentifiers,
        direction: msg.key.fromMe ? 'outgoing' : 'incoming',
        recipient_id: recipientId,
        actual_sender: actualSender,
        originating_time: messageTimestamp,
    };
}



// --- Command Line Arguments ---
const args = process.argv.slice(2);
const port = args[0] || 9000; // Default to port 9000 if not provided

// --- MongoDB Auth State Logic ---
const useMongoDBAuthState = async (userId, collection) => {
    const reviveBuffers = (key, value) => {
        if (value && typeof value === 'object' && value.type === 'Buffer') {
            if (Array.isArray(value.data)) {
                return Buffer.from(value.data);
            }
            if (typeof value.data === 'string') {
                return Buffer.from(value.data, 'base64');
            }
        }
        return value;
    };

    const serializeBuffers = (key, value) => {
        // Because JSON.stringify calls toJSON on Buffers before hitting this replacer,
        // we see { type: 'Buffer', data: [numbers...] } instead of a Buffer instance.
        if (value && value.type === 'Buffer' && Array.isArray(value.data)) {
            return { type: 'Buffer', data: Buffer.from(value.data).toString('base64') };
        }
        if (value instanceof Buffer) {
            return { type: 'Buffer', data: value.toString('base64') };
        }
        if (value instanceof Uint8Array) {
            return { type: 'Buffer', data: Buffer.from(value).toString('base64') };
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
            try {
                const parsed = JSON.parse(doc.value, reviveBuffers);
                // Sanity check: If we loaded a session-related key and it looks like a "corrupted" buffer object
                // (has keys "0", "1" etc but isn't a Buffer), warn about it.
                if (parsed && typeof parsed === 'object' && !Buffer.isBuffer(parsed) && !Array.isArray(parsed)) {
                    const keys = Object.keys(parsed);
                    if (keys.length > 0 && keys.every(k => !isNaN(parseInt(k)))) {
                        console.warn(`[${userId}] WARNING: Loaded key '${key}' appears to be a corrupted Buffer (stored as object). This may cause Bad MAC errors.`);
                    }
                }
                return parsed;
            } catch (e) {
                console.error(`[${userId}] Error parsing data for key '${key}':`, e);
                return null;
            }
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

    // In-memory cache to prevent race conditions during rapid updates
    const keysCache = {};

    return {
        state: {
            creds,
            keys: {
                get: async (type, ids) => {
                    const data = {};
                    await Promise.all(
                        ids.map(async id => {
                            const cacheKey = `${type}-${id}`;
                            if (cacheKey in keysCache) {
                                if (keysCache[cacheKey]) {
                                    data[id] = keysCache[cacheKey];
                                }
                                return;
                            }

                            let value = await readData(`${userId}-${type}-${id}`);
                            if (value) {
                                data[id] = value;
                                keysCache[cacheKey] = value;
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
                            const cacheKey = `${type}-${id}`;
                            keysCache[cacheKey] = value; // Update cache immediately
                            promises.push(writeData(`${userId}-${type}-${id}`, value));
                        }
                    }
                    await Promise.all(promises);
                },
                remove: async (type, ids) => {
                    const promises = [];
                    for (const id of ids) {
                        const cacheKey = `${type}-${id}`;
                        delete keysCache[cacheKey]; // Remove from cache immediately
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

// Helper to manage LID mappings in MongoDB
const loadLidMappings = async (userId) => {
    try {
        const key = `${userId}-lid-mappings`;
        console.log(`[${userId}] Loading LID mappings from DB key: ${key}`);
        const doc = await baileysSessionsCollection.findOne({ _id: key });
        return doc?.mappings || {};
    } catch (e) {
        console.error(`[${userId}] Failed to load LID mappings:`, e);
        return {};
    }
};

const saveLidMapping = async (userId, lid, pn) => {
    try {
        const key = `${userId}-lid-mappings`;
        const update = {};
        update[`mappings.${lid}`] = pn;
        await baileysSessionsCollection.updateOne(
            { _id: key },
            { $set: update },
            { upsert: true }
        );
        console.log(`[${userId}] Persisted LID mapping: ${lid} -> ${pn}`);
    } catch (e) {
        console.error(`[${userId}] Failed to save LID mapping:`, e);
    }
};

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

    // Pre-load LID mappings to ensure consistent state for auth/socket initialization
    const lidMappings = await loadLidMappings(userId);

    // Initialize session placeholder if needed, or update cache immediately
    // This ensures resolveId has the correct state during useMongoDBAuthState initialization
    if (!sessions[userId]) {
        console.log(`[${userId}] Creating new session object (pre-init).`);
        sessions[userId] = {
            contactsCache: {},
            lidCache: lidMappings,
            pushNameCache: {},
            vendorConfig: vendorConfig,
            retryCount: 0,
            http405Tracker: createHttp405Tracker(),
            store: { messages: {} }, // Initialize in-memory message store
            authState: null // Placeholder for auth state
            // sock etc will be set later
        };
    } else {
        console.log(`[${userId}] Updating existing session object (pre-init).`);
        sessions[userId].lidCache = lidMappings;
        if (!sessions[userId].store) {
            sessions[userId].store = { messages: {} }; // Initialize in-memory message store if missing
        }
    }

    // Reuse existing auth state if available (preserves in-memory keys during restarts)
    // Otherwise, initialize from MongoDB
    let authState = sessions[userId].authState;
    if (!authState) {
        console.log(`[${userId}] Initializing new MongoDB auth state.`);
        authState = await useMongoDBAuthState(userId, baileysSessionsCollection);
        sessions[userId].authState = authState;
    } else {
        console.log(`[${userId}] Reusing existing in-memory auth state (preserving keys).`);
    }

    const { state, saveCreds } = authState;

    const logger = pino({ level: 'debug' });

    // DEBUG: Check Auth State 'me'
    if (state && state.creds && state.creds.me) {
        console.log(`[${userId}] Auth State 'me': ${JSON.stringify(state.creds.me)}`);
    } else {
        console.log(`[${userId}] Auth State 'me' is empty or missing.`);
    }

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
        sessions[userId].lidCache = {}; // Reset cache on reconnect (will load from DB below)
        sessions[userId].pushNameCache = {}; // Reset pushName cache
        resetHttp405Tracker(sessions[userId]);
        // Do not reset store here, preserve what we have?
        // Or reset if it's a new connection?
        // If we restart the connection logic, likely we should keep the store as long as the process lives.
        if (!sessions[userId].store) {
            sessions[userId].store = { messages: {} };
        }
    } else {
        console.log(`[${userId}] Creating new session object.`);
        sessions[userId] = {
            sock: sock,
            currentQR: null,
            connectionStatus: 'connecting',
            contactsCache: {},
            lidCache: {}, // Initialize empty (will load from DB below)
            pushNameCache: {},
            vendorConfig: vendorConfig,
            retryCount: 0,
            http405Tracker: createHttp405Tracker(),
            store: { messages: {} }, // Initialize in-memory message store
            authState: authState // Store auth state
        };
    }

    // Load persisted LID mappings asynchronously to avoid blocking session creation
    // This resolves a race condition where the WebSocket connects before this function returns
    loadLidMappings(userId).then(mappings => {
        if (sessions[userId]) {
            sessions[userId].lidCache = mappings;
            console.log(`[${userId}] Loaded ${Object.keys(mappings).length} LID mappings from DB into session.`);
        }
    });


    // Register credentials update listener to persist session state
    sock.ev.on('creds.update', saveCreds);

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
            // Log user info to help debug LID issues
            if (session.sock?.user) {
                console.log(`[${userId}] Session user info: ${JSON.stringify(session.sock.user)}`);

                // Active Self-LID Resolution
                const selfId = jidNormalizedUser(session.sock.user.id);
                if (selfId && !session.sock.user.lid) {
                    console.log(`[${userId}] Self LID missing in session. Actively querying onWhatsApp for ${selfId}...`);
                    session.sock.onWhatsApp(selfId).then(results => {
                        if (results && results[0]) {
                            const data = results[0];
                            if (data.exists && data.jid) {
                                // onWhatsApp returns the JID you queried (PN).
                                // We need the LID. Does it return LID? 
                                // Actually onWhatsApp usually confirms existence. 
                                // Let's try to 'get' the contact/profile which might resolve it?
                                // Or check if result has 'lid' property (some versions do).
                                // If not, we might need another method, but let's log what we get.
                                console.log(`[${userId}] onWhatsApp result: ${JSON.stringify(data)}`);

                                // If result has lid, save it.
                                if (data.lid) {
                                    const foundLid = jidNormalizedUser(data.lid);
                                    saveLidMapping(userId, foundLid, selfId);
                                    session.lidCache[foundLid] = selfId;
                                    console.log(`[${userId}] Resolved Self LID via onWhatsApp: ${foundLid} -> ${selfId}`);
                                }
                            }
                        }
                    }).catch(err => {
                        console.error(`[${userId}] Failed to query onWhatsApp for self:`, err);
                    });
                }
            }
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

            if (session.isGracefulDisconnect) {
                console.log(`[${userId}] Graceful disconnect detected. Skipping reconnect logic.`);
                session.isGracefulDisconnect = false; // Reset the flag
                return;
            }

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
        } catch (e) {
            console.error(`[${userId}] Error saving credentials:`, e);
        }
    });

    sock.ev.on('contacts.update', (updates) => {
        const session = sessions[userId];
        if (!session) return;
        processContacts(session, userId, updates);
    });

    sock.ev.on('contacts.upsert', (updates) => {
        const session = sessions[userId];
        if (!session) return;
        processContacts(session, userId, updates);
    });

    sock.ev.on('messaging-history.set', async ({ messages, contacts, isLatest }) => {
        try {
            const session = sessions[userId];
            if (!session) return;

            console.log(`[${userId}] messaging-history.set received. Msgs: ${messages?.length}, Contacts: ${contacts?.length}, isLatest: ${isLatest}`);

            if (contacts) {
                processContacts(session, userId, contacts);
                console.log(`[${userId}] messaging-history.set: Cached ${contacts.length} contacts.`);
            }

            if (session.store && messages) {
                let addedCount = 0;
                // messages in history.set can be an array of WAMessage directly
                // or sometimes an array of Chat objects with messages.
                // We handle the direct WAMessage array case primarily.
                for (const item of messages) {
                    // Check if item is a message (has key)
                    if (item.key && item.message) {
                        const msg = item;
                        const jid = msg.key.remoteJid;
                        if (!session.store.messages[jid]) {
                            session.store.messages[jid] = [];
                        }
                        session.store.messages[jid].push(msg);
                        if (session.store.messages[jid].length > 1000) {
                            session.store.messages[jid].shift();
                        }
                        addedCount++;
                    }
                }
                console.log(`[${userId}] messaging-history.set: Added ${addedCount} messages to store.`);
            }
        } catch (e) {
            console.error(`[${userId}] Error in messaging-history.set handler:`, e);
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        try {
            const session = sessions[userId];
            if (!session) return;

            console.log(`[${userId}] messages.upsert type: ${m.type}, count: ${m.messages.length}`);

            // Populate internal store with RAW messages, irrespective of processing logic
            if (session.store && m.messages) {
                for (const msg of m.messages) {
                    const jid = msg.key.remoteJid;
                    if (!session.store.messages[jid]) {
                        session.store.messages[jid] = [];
                    }
                    // Simple buffer: append and slice
                    session.store.messages[jid].push(msg);
                    if (session.store.messages[jid].length > 1000) {
                        session.store.messages[jid].shift();
                    }
                    if (m.type === 'append' || m.type === 'notify') {
                        // Log first message of batch for debug
                        if (m.messages.indexOf(msg) === 0) {
                            console.log(`[${userId}] Stored message in buffer for ${jid}. ID: ${msg.key.id}`);
                        }
                    }
                }
            }

            // If we are receiving messages, we can consider the connection open
            if (session.connectionStatus !== 'open') {
                console.log(`[${userId}] Received messages while not in 'open' state, updating status.`);
                session.connectionStatus = 'open';
            }

            const processOffline = session.vendorConfig.process_offline_messages === true;
            const allowGroups = session.vendorConfig.allow_group_messages === true;

            const newMessagesPromises = m.messages.map(async (msg) => {
                return await processMessage(session, userId, msg, processOffline, allowGroups);
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
        // Do NOT automatically convert LID to PN.
        // Sending to the LID ensures we use the correct cryptographic session (LID session),
        // preventing "Bad MAC" errors caused by state divergence when mixing PN/LID sessions.

        if (!recipient.endsWith('@g.us') && !recipient.endsWith('@s.whatsapp.net') && !recipient.endsWith('@lid')) {
            const [result] = await session.sock.onWhatsApp(recipient);
            if (!result?.exists) {
                return res.status(400).json({ error: `Recipient ${recipient} is not on WhatsApp.` });
            }
        }
        const sentMsgData = await session.sock.sendMessage(recipient, { text: message });
        console.log(`[${userId}] sendMessage() invoked for ${recipient}`);

        // Learn self LID from sent message (especially for group messages)
        if (sentMsgData?.key?.participant && sentMsgData.key.participant.endsWith('@lid')) {
            const selfId = jidNormalizedUser(session.sock?.user?.id);
            const participantLid = jidNormalizedUser(sentMsgData.key.participant);
            if (selfId && participantLid) {
                if (!session.lidCache) session.lidCache = {};
                if (session.lidCache[participantLid] !== selfId) {
                    session.lidCache[participantLid] = selfId;
                    console.log(`[${userId}] Learned Self LID from sendMessage: ${participantLid} -> ${selfId}`);
                    saveLidMapping(userId, participantLid, selfId);
                }
            }
        }

        res.status(200).json({
            status: 'Message sent',
            recipient,
            message,
            provider_message_id: sentMsgData.key.id
        });
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
    // console.log(`[${userId}] Returning status:`, { status: apiStatus || 'initializing', hasQR: !!session.currentQR });
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

app.post('/sessions/:userId/groups', async (req, res) => {
    const { userId } = req.params;
    const session = sessions[userId];
    if (!session || !session.sock) {
        return res.status(404).json({ error: 'Session not found.' });
    }
    try {
        const groups = await session.sock.groupFetchAllParticipating();
        const groupList = Object.values(groups).map(g => ({
            id: g.id,
            subject: g.subject
        }));
        res.status(200).json({ groups: groupList });
    } catch (e) {
        console.error(`[${userId}] Error fetching groups:`, e);
        res.status(500).json({ error: 'Failed to fetch groups.' });
    }
});

app.post('/sessions/:userId/fetch-messages', async (req, res) => {
    const { userId } = req.params;
    const { groupId, limit } = req.body;
    const session = sessions[userId];
    if (!session || !session.sock) {
        return res.status(404).json({ error: 'Session not found.' });
    }
    if (!groupId) {
        return res.status(400).json({ error: 'groupId is required.' });
    }

    try {
        console.log(`[${userId}] Fetching ${limit} historic messages for ${groupId}...`);

        let messages = [];

        // Try using fetchMessagesFromWA if available (common in forks)
        if (typeof session.sock.fetchMessagesFromWA === 'function') {
            // Example signature: (jid, count, cursor)
            // We want the last 'limit' messages.
            // We can pass `undefined` for cursor to get latest.
            const result = await session.sock.fetchMessagesFromWA(groupId, limit);
            messages = result || [];
        } else if (session.store && session.store.messages[groupId]) {
            // Use local store buffer (active provider state)
            const storedMessages = session.store.messages[groupId];
            console.log(`[${userId}] Using local store buffer for ${groupId}. Found ${storedMessages.length} total messages.`);
            // Get last 'limit' messages
            messages = storedMessages.slice(-limit);
        } else {
            console.warn(`[${userId}] Active fetch failed and no local store data for ${groupId}.`);

            // If store is not initialized at all, we can't do anything
            if (!session.store) {
                throw new Error("Active history fetching is not supported by the current Baileys provider version (no store).");
            }
            // If store exists but no messages for this group, return empty (valid result)
            messages = [];
        }

        const allowGroups = true; // We are fetching for a group specifically
        const processOffline = true; // We always want these messages to be processed/formatted

        const processedMessagesPromises = messages.map(async (msg) => {
            // Reuse the extraction logic
            return await processMessage(session, userId, msg, processOffline, allowGroups);
        });

        const processedMessages = (await Promise.all(processedMessagesPromises)).filter(Boolean);

        console.log(`[${userId}] fetch-messages: Returning ${processedMessages.length} messages after processing.`);
        res.status(200).json({ messages: processedMessages });

    } catch (e) {
        console.error(`[${userId}] Error fetching historic messages:`, e);
        res.status(500).json({ error: e.message || 'Failed to fetch historic messages.' });
    }
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

            ws.on('message', async (message) => {
                try {
                    const data = JSON.parse(message);
                    if (data.action === 'disconnect') {
                        console.log(`[${userId}] Received disconnect command (cleanup: ${data.cleanup_session}).`);
                        const session = sessions[userId];
                        if (session && session.sock) {
                            if (data.cleanup_session) {
                                session.isUnlinking = true;
                                await session.sock.logout();
                                const deleteResult = await baileysSessionsCollection.deleteMany({ _id: { $regex: `^${userId}-` } });
                                console.log(`[${userId}] Deleted ${deleteResult.deletedCount} auth entries from MongoDB.`);
                                delete sessions[userId];
                            } else {
                                // Graceful disconnect without clearing session
                                session.isGracefulDisconnect = true;
                                session.sock.end(undefined);
                            }
                        }
                    }
                } catch (e) {
                    console.error(`[WebSocket] Error processing message for userId ${userId}:`, e);
                }
            });

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
