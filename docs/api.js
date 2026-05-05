/**
 * GitHub API integration wrapper
 */

const API = {
    owner: 'eyezter752-jpg',
    repo: 'nutrition-dashboard',
    branch: 'main',

    getToken() {
        const encrypted = localStorage.getItem('github_token_encrypted');
        if (!encrypted) return null;
        return encrypted;
    },

    async decryptToken(password) {
        const encrypted = localStorage.getItem('github_token_encrypted');
        if (!encrypted) return null;
        try {
            const obj = JSON.parse(encrypted);
            const decrypted = await decrypt(password, obj.salt, obj.iv, obj.ciphertext);
            return decrypted.token;
        } catch {
            return null;
        }
    },

    async encryptAndStoreToken(token, password) {
        if (!token || !password) {
            throw new Error('Token and password are required');
        }

        try {
            const encrypted = await encrypt({ token }, password);
            localStorage.setItem('github_token_encrypted', JSON.stringify(encrypted));
            console.log('✓ Token encrypted and stored');
        } catch (err) {
            console.error('Encryption failed:', err);
            throw new Error('Failed to encrypt token: ' + (err?.message || err));
        }
    },

    async makeRequest(endpoint, method = 'GET', data = null, token = null) {
        const url = `https://api.github.com${endpoint}`;
        const headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        };

        if (token) {
            headers['Authorization'] = `token ${token}`;
        }

        const options = {
            method,
            headers
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        return await response.text();
    },

    async getFile(path, token) {
        try {
            return await this.makeRequest(
                `/repos/${this.owner}/${this.repo}/contents/${path}`,
                'GET',
                null,
                token
            );
        } catch {
            return null;
        }
    },

    async putFile(path, content, message, token) {
        // Get current file SHA if it exists
        let sha = null;
        const existing = await this.getFile(path, token);
        if (existing) {
            sha = existing.sha;
        }

        const data = {
            message,
            content: btoa(unescape(encodeURIComponent(content))),
            branch: this.branch
        };

        if (sha) {
            data.sha = sha;
        }

        return await this.makeRequest(
            `/repos/${this.owner}/${this.repo}/contents/${path}`,
            'PUT',
            data,
            token
        );
    },

    async saveMeal(date, encrypted, token) {
        const path = `meals/${date}.json.enc`;
        const content = JSON.stringify(encrypted);
        return await this.putFile(path, content, `meals: update ${date}`, token);
    },

    async saveWeight(weightData, token) {
        const content = JSON.stringify(weightData, null, 2);
        return await this.putFile('data/weight.json', content, 'data: update weight', token);
    },

    async loadProducts(token) {
        try {
            const response = await this.makeRequest(
                `/repos/${this.owner}/${this.repo}/contents/data/products.json`,
                'GET',
                null,
                token
            );
            const decoded = atob(response.content);
            return JSON.parse(decoded);
        } catch {
            return [];
        }
    },

    async loadDailyData(token) {
        try {
            const response = await this.makeRequest(
                `/repos/${this.owner}/${this.repo}/contents/data/daily.json`,
                'GET',
                null,
                token
            );
            const decoded = atob(response.content);
            return JSON.parse(decoded);
        } catch {
            return {};
        }
    },

    async loadWeightData(token) {
        try {
            const response = await this.makeRequest(
                `/repos/${this.owner}/${this.repo}/contents/data/weight.json`,
                'GET',
                null,
                token
            );
            const decoded = atob(response.content);
            return JSON.parse(decoded);
        } catch {
            return {};
        }
    }
};
