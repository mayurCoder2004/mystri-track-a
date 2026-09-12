"""Starter checks exercise basic setup. They are not complete acceptance coverage."""
import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self.tmp.name) / 'demo.sqlite3')
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_seed_is_repeatable(self):
        storage.seed(self.db)
        self.assertEqual(len(reporting.invoices(self.db)), 6)

    def test_seed_summary(self):
        summary = reporting.overview(self.db)['summary']
        self.assertEqual(summary['invoice_count'], 6)
        self.assertEqual(summary['outstanding'], 3209.99)

    def test_one_valid_invoice(self):
        result = importing.import_csv(self.db, 'customer_id,invoice_number,amount,due_date\nHARBOR,SMOKE-1,25.00,2026-09-09\n', 'invoices')
        self.assertEqual(result['imported'], 1)

    def test_payment_reference_when_amount_is_unique(self):
        result = importing.import_csv(self.db, 'payment_id,customer_id,invoice_number,amount\nSMOKE-P1,HARBOR,INV-100,20.00\n', 'payments')
        self.assertEqual(result['imported'], 1)
        invoice = next(r for r in reporting.invoices(self.db) if r['invoice_number'] == 'INV-100')
        self.assertEqual(invoice['paid'], 20.00)

    def test_payment_does_not_match_by_amount(self):
        result = importing.import_csv(
            self.db,
            'payment_id,customer_id,invoice_number,amount\n'
            'SMOKE-P2,MAPLE,INV-NOT-FOUND,1250.00\n',
            'payments',
        )

        self.assertEqual(result['imported'], 1)

        harbor_invoice = next(
            r for r in reporting.invoices(self.db)
            if r['invoice_number'] == 'INV-100'
        )
        self.assertEqual(harbor_invoice['paid'], 0.00)

        unmatched = reporting.overview(self.db)['unmatched_payments']
        payment = next(
            p for p in unmatched
            if p['payment_id'] == 'SMOKE-P2'
        )
        self.assertEqual(payment['amount'], 1250.00)

    def test_duplicate_invoice_is_skipped(self):
        csv = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,SMOKE-DUP-1,1250.00,2026-09-15\n'
        )

        first = importing.import_csv(self.db, csv, 'invoices')
        second = importing.import_csv(self.db, csv, 'invoices')

        self.assertEqual(first['imported'], 1)
        self.assertEqual(second['skipped'], 1)

        invoices = [
            r for r in reporting.invoices(self.db)
            if r['customer_id'] == 'HARBOR'
            and r['invoice_number'] == 'SMOKE-DUP-1'
        ]
        self.assertEqual(len(invoices), 1)

    def test_invoice_identity_change_is_rejected(self):
        original = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,SMOKE-ID-1,500.00,2026-09-15\n'
        )
        changed = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,SMOKE-ID-1,600.00,2026-09-15\n'
        )

        first = importing.import_csv(self.db, original, 'invoices')
        second = importing.import_csv(self.db, changed, 'invoices')

        self.assertEqual(first['imported'], 1)
        self.assertEqual(second['rejected'], 1)
        self.assertEqual(second['errors'][0]['line'], 2)

        invoice = next(
            r for r in reporting.invoices(self.db)
            if r['customer_id'] == 'HARBOR'
            and r['invoice_number'] == 'SMOKE-ID-1'
        )
        self.assertEqual(invoice['amount'], 500.00)
        self.assertEqual(invoice['due_date'], '2026-09-15')

    def test_invalid_row_does_not_abort_import(self):
        csv = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,SMOKE-ROW-1,100.00,2026-09-15\n'
            'MAPLE,SMOKE-ROW-2,not-a-number,2026-09-16\n'
            'NORTH,SMOKE-ROW-3,200.00,2026-09-17\n'
        )

        result = importing.import_csv(self.db, csv, 'invoices')

        self.assertEqual(result['imported'], 2)
        self.assertEqual(result['rejected'], 1)
        self.assertEqual(result['errors'][0]['line'], 3)

        self.assertIsNotNone(
            next(
                r for r in reporting.invoices(self.db)
                if r['invoice_number'] == 'SMOKE-ROW-1'
            )
        )
        self.assertIsNotNone(
            next(
                r for r in reporting.invoices(self.db)
                if r['invoice_number'] == 'SMOKE-ROW-3'
            )
        )

    def test_invoice_status_filter_distinguishes_open_and_paid(self):
        open_invoices = reporting.invoices(self.db, 'open')
        paid_invoices = reporting.invoices(self.db, 'paid')

        self.assertTrue(open_invoices)
        self.assertTrue(paid_invoices)

        self.assertTrue(all(invoice['status'] == 'open' for invoice in open_invoices))
        self.assertTrue(all(invoice['status'] == 'paid' for invoice in paid_invoices))

    def test_export_has_header(self):
        self.assertTrue(reporting.export_csv(self.db).startswith('customer_id,invoice_number,amount,paid,balance,status'))


if __name__ == '__main__':
    unittest.main()
