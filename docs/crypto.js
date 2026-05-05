/**
 * Расшифровка и шифрование AES-256-GCM через WebCrypto API
 * Совместимо с PBKDF2 из Python cryptography
 */

function b64ToBytes(b64) {
    const binaryString = atob(b64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}

function bytesToB64(bytes) {
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

async function deriveKey(password, salt) {
    const enc = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
        "raw",
        enc.encode(password),
        { name: "PBKDF2" },
        false,
        ["deriveKey"]
    );

    return await crypto.subtle.deriveKey(
        {
            name: "PBKDF2",
            salt: salt,
            iterations: 100000,
            hash: "SHA-256"
        },
        keyMaterial,
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"]
    );
}

async function decrypt(password, saltB64, ivB64, ciphertextB64) {
    try {
        const salt = b64ToBytes(saltB64);
        const iv = b64ToBytes(ivB64);
        const ciphertext = b64ToBytes(ciphertextB64);

        const key = await deriveKey(password, salt);
        const plaintext = await crypto.subtle.decrypt(
            { name: "AES-GCM", iv: iv },
            key,
            ciphertext
        );

        const jsonStr = new TextDecoder().decode(plaintext);
        return JSON.parse(jsonStr);
    } catch (err) {
        console.error('Ошибка расшифровки:', err);
        throw err;
    }
}

async function encrypt(data, password) {
    try {
        const enc = new TextEncoder();

        // Генерируем случайные salt (16 bytes) и IV (12 bytes)
        const salt = crypto.getRandomValues(new Uint8Array(16));
        const iv = crypto.getRandomValues(new Uint8Array(12));

        const key = await deriveKey(password, salt);

        const plaintext = enc.encode(JSON.stringify(data));
        const ciphertext = await crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv },
            key,
            plaintext
        );

        return {
            salt: bytesToB64(salt),
            iv: bytesToB64(iv),
            ciphertext: bytesToB64(new Uint8Array(ciphertext))
        };
    } catch (err) {
        console.error('Ошибка шифрования:', err);
        throw err;
    }
}
