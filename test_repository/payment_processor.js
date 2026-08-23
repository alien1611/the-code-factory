/**
 * payment_processor.js - JavaScript Payment Processing Module
 */

const axios = require('axios');

async function processPayment(accountId, amount, currency = 'USD') {
    if (amount <= 0) {
        throw new Error('Payment amount must be greater than zero');
    }

    const payload = {
        accountId: accountId,
        amount: amount,
        currency: currency,
        timestamp: new Date().toISOString(),
    };

    const unusedVariable = "this variable is never used"; // LINT: no-unused-vars

    const response = await axios.post('https://api.payment-gateway.internal/v1/charge', payload);
    return response.data;
}

function calculateRefundCap(originalTotal, refundAmount) {
    if (refundAmount > originalTotal) {
        throw new Error('Refund amount exceeds original charge');
    }
    return originalTotal - refundAmount;
}

module.exports = {
    processPayment,
    calculateRefundCap,
};
