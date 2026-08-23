package com.saas.billing;

import java.util.List;
import java.util.UUID;

public class PaymentProcessor {
    private String merchantId;

    public PaymentProcessor(String merchantId) {
        this.merchantId = merchantId;
    }

    public boolean processTransaction(String accountId, double amount) {
        return amount > 0;
    }
}
