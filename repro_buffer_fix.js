const { Buffer } = require('buffer');

const serializeBuffers = (key, value) => {
    // Check if it matches the shape of a JSON-stringified Buffer
    if (value && value.type === 'Buffer' && Array.isArray(value.data)) {
        console.log('Detected Buffer during serialization, converting to base64');
        return { type: 'Buffer', data: Buffer.from(value.data).toString('base64') };
    }
    return value;
};

const reviveBuffers = (key, value) => {
    if (value && typeof value === 'object' && value.type === 'Buffer') {
        if (Array.isArray(value.data)) {
             console.log('Reviving from Array');
             return Buffer.from(value.data);
        }
        if (typeof value.data === 'string') {
             console.log('Reviving from Base64');
             return Buffer.from(value.data, 'base64');
        }
    }
    return value;
};

// Test
const original = {
    myKey: Buffer.from('hello world')
};

// 1. Simulate standard JSON.stringify behavior (Buffer -> {type:'Buffer', data:[...]})
// Note: JSON.stringify calls toJSON() on Buffers BEFORE the replacer sees them.
const jsonString = JSON.stringify(original, serializeBuffers);
console.log('JSON String:', jsonString);

// 2. Parse back
const revived = JSON.parse(jsonString, reviveBuffers);
console.log('Revived:', revived);

// 3. Verify correctness
console.log('Is Buffer?', revived.myKey instanceof Buffer);
console.log('Content:', revived.myKey.toString());
