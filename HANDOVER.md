# ClearLedger — Track A Handover

## Summary

Investigated the supplied ClearLedger invoice register, reproduced the seeded defects, prioritized correctness and data-integrity issues, and implemented focused fixes without changing the supplied fixtures or public API routes.

## Findings and fixes

1. **Payment matching — High:** Payments were matched by amount, which could attach a payment to the wrong invoice when amounts were shared. Matching now requires both `customer_id` and `invoice_number`.

2. **Duplicate invoice identity — High:** Re-importing an existing invoice could create duplicate records. Imports now skip an identical `(customer_id, invoice_number, amount, due_date)` and reject the same identity when details differ.

3. **Invalid CSV row handling — High:** Normalization errors could abort the entire import. Validation is now isolated per row so valid rows continue processing and rejected rows report their CSV line number and reason.

4. **Invoice status filtering — Medium:** The open/paid filter selected the wrong status. Filtering now correctly distinguishes `open`, `paid`, and `all`.

5. **Browser import feedback — Medium:** The browser previously treated unsuccessful HTTP responses as successful imports. It now checks the response status/body, displays useful errors, shows imported/skipped/rejected counts, and refreshes after successful processing.

6. **Money export precision — High:** Float/truncation behavior could change values such as `19.99` to `19.98`. Export formatting now uses `Decimal` quantization to preserve two-decimal money values.

## Verification

Added six regression tests covering payment identity, duplicate invoices, conflicting invoice identity, invalid-row isolation, status filtering, and two-decimal export precision.

The final suite passes:

The command is:

python -m unittest discover -s tests -v

11 tests passed.

Also restored and verified the supplied fixture before/after changes. The original register remained intact; persistence was checked by importing a temporary invoice/payment, restarting the application, and confirming the records remained correct.

## Small improvement

Import feedback now includes the selected filename, making it easier to confirm which CSV was processed.

## AI/tool usage

- **Suggestion:** use invoice identity rather than payment amount for matching. **Decision:** accepted because the business rules define payment/invoice identity explicitly. **Check:** added a regression case where amount alone is ambiguous.
- **Suggestion:** isolate CSV normalization errors per row. **Decision:** accepted because one invalid row should not reject valid rows. **Check:** added a mixed valid/invalid CSV test.
- **Suggestion:** use decimal arithmetic for exported money. **Decision:** accepted after reproducing `19.99 → 19.98` behavior. **Check:** added a regression test confirming exact two-decimal output.

No known required behavior remains intentionally unfinished.


