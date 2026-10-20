# Failure injection evidence

| case | broken | symptom | verdict | mechanism | recovery | seconds |
|---|---|---|---|---|---|---|
| a | Removed `customer_unique_id` from an isolated CSV source copy | schema mismatch names missing=['customer_unique_id'] | TERTANGKAP | central contract compares the complete header before conversion or load | restore the last bronze version | 0.1 |
| b | Ran the 5,000-order producer twice without resetting state | stored rows stayed 394,713; second replay ignored 21,450 valid duplicates | TERTANGKAP | deterministic event IDs plus primary-key conflict handling | none; replay is idempotent | 21.9 |
| c | Worker committed PostgreSQL then exited 137 before Kafka offset commit | message redelivered; one PK row, attempts=2 | TERTANGKAP | database commit precedes manual offset commit; PK handles redelivery | restart the same consumer group | 9.4 |
| d | Stopped local Kafka for 3 seconds while 1,000 messages were being produced | delivered=1000, failed=0 after broker recovery | TERTANGKAP | acks=all, delivery callbacks, buffering, retries, and checked flush | service manager restarts Kafka; resend only if callbacks report failures | 8.43 |
| e | Reran bronze → silver → load → model → marts unchanged | compared 19 table counts; differences=0; bronze={'unchanged'} | TERTANGKAP | SHA-256 manifest and transactional full replacements | none; rerun is safe | 23.0 |
