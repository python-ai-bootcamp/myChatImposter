const { MongoClient } = require('mongodb');

async function debugMongo() {
    const mongoUrl = process.env.MONGODB_URL || 'mongodb://mongodb:27017';
    // Fallback for localhost if running outside docker but port forwarded
    // const mongoUrlLocal = 'mongodb://localhost:27017'; 

    // START EDIT: Using localhost since we are running on host
    const url = 'mongodb://localhost:27017';
    // END EDIT

    console.log(`Connecting to MongoDB at ${url}`);
    const client = new MongoClient(url);

    try {
        await client.connect();
        const db = client.db('chat_manager');
        const collection = db.collection('baileys_sessions');

        console.log(`Checking collection: ${collection.collectionName}`);
        const count = await collection.countDocuments({});
        console.log(`Total documents: ${count}`);

        const cursor = collection.find({});
        console.log("-".repeat(30));
        while (await cursor.hasNext()) {
            const doc = await cursor.next();
            console.log(`ID: ${doc._id}`);
        }
        console.log("-".repeat(30));

    } catch (e) {
        console.error(`Error: ${e.message}`);
    } finally {
        await client.close();
    }
}

debugMongo();
