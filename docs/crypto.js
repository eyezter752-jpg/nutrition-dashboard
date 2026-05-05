/**
 * Расшифровка AES-256-GCM через WebCrypto API
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

async function decrypt(password, saltB64, ivB64, ciphertextB64) {
    try {
        const enc = new TextEncoder();
        const salt = b64ToBytes(saltB64);
        const iv = b64ToBytes(ivB64);
        const ciphertext = b64ToBytes(ciphertextB64);

        // Импортируем пароль как ключевой материал
        const keyMaterial = await crypto.subtle.importKey(
            "raw",
            enc.encode(password),
            { name: "PBKDF2" },
            false,
            ["deriveKey"]
        );

        // Выводим ключ через PBKDF2
        const key = await crypto.subtle.deriveKey(
            {
                name: "PBKDF2",
                salt: salt,
                iterations: 100000,
                hash: "SHA-256"
            },
            keyMaterial,
            { name: "AES-GCM", length: 256 },
            false,
            ["decrypt"]
        );

        // Расшифровываем
        const plaintext = await crypto.subtle.decrypt(
            { name: "AES-GCM", iv: iv },
            key,
            ciphertext
        );

        // Парсим JSON
        const jsonStr = new TextDecoder().decode(plaintext);
        return JSON.parse(jsonStr);
    } catch (err) {
        console.error('Ошибка расшифровки:', err);
        throw err;
    }
}
