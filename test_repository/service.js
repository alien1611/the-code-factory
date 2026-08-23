import axios from 'axios';
const fs = require('fs');

export async function fetchUserData(userId, options = {}) {
    const response = await axios.get(`/users/${userId}`);
    return response.data;
}

const computeTotal = (items, taxRate = 0.05) => {
    return items.reduce((acc, curr) => acc + curr.price, 0) * (1 + taxRate);
};

class AuthManager {
    constructor(secretKey) {
        this.secretKey = secretKey;
    }

    validateToken(token) {
        return token.startsWith('bearer-');
    }
}
