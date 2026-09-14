# Offline resilience contract

AfyaSync does not silently fabricate payer, clinical or payment outcomes while disconnected. Facility workflows may continue where their domain permits, while external operations are represented as retryable integration transactions. Any future offline client must use durable local queues, idempotency keys, explicit sync states and conflict handling before being enabled for live clinical use.
