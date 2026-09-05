# Portfolio upgrade validation

Validation performed on 5 September 2026 with Python 3.11, Django 4.2.7, DRF 3.14.0,
and isolated SQLite test/demo databases.

## Baseline and phase checkpoints

| Checkpoint | Django check | Tests |
| --- | --- | --- |
| Before changes | No issues | 42 passed |
| Phase 4: transaction and authorization fixes | No issues | 56 passed |
| Phase 5: shared responsive interface | No issues | 56 passed |
| Phase 6: inventory tracking | No issues | 69 passed |
| Phase 7: dashboard analytics | No issues | 72 passed |
| Phase 8: final validation | No issues | 83 passed |

Baseline defects included a missing cashier template, cashier transactions without
an owner, a missing transaction-create template, unscoped detail CRUD, writable
transaction status, conflicting cart item routes, and early returns that committed
partial checkout stock changes. The upgrade adds regression coverage for these
paths and preserves the existing Django/DRF architecture.

## Final automated checks

- `python manage.py check`: no issues.
- `python manage.py makemigrations --check`: no changes detected.
- `python manage.py test`: 83 passed, 0 failures, 0 errors.
- `python manage.py spectacular --validate --fail-on-warn`: successful; no warnings
  or schema errors. Exported schema was stored outside the repository.
- Ruff import/unused-name checks on changed application modules and new tests:
  passed. Original migration history was retained.
- `git diff --check`: no whitespace errors after cleanup.

Tests cover the original 42 cases plus ownership on all detail/cart methods,
atomic multi-item rollback, zero quantities, duplicate products, immutable paid
transactions, HTML cashier and payment, staff restrictions, expiry boundaries,
restock and audit rollback, protected history, dashboard aggregation and isolation,
seed safety/idempotency, all HTML templates, pagination, CSRF, OpenAPI, historical
unit prices, multipart cart requests, and legacy multiple-draft selection.

## Real browser checks

Headless Chrome ran against Django `runserver` bound to `127.0.0.1:8765`, using a
fresh temporary database and demo account with a random private password. The
server was stopped after validation; credentials and database were not committed.

- Login through the HTML form succeeded.
- Dashboard chart initialized with actual backend data.
- `/`, `/obat/`, `/kasir/`, transaction detail, and `/api/docs/` returned HTTP 200.
- Dashboard, inventory, cashier and transaction lists had no page-level horizontal
  overflow at 768 px and 390 px. Tables retain their own horizontal scroll.
- The mobile menu opened and closed successfully.
- Cashier added a row, estimated a subtotal/total, checked out two units, and
  completed the simulated payment via the HTML UI.
- No JavaScript page errors were observed.
- Six real screenshots were captured and visually reviewed; see
  [the screenshot gallery](screenshots/README.md).

The first browser run passed application checks but its temporary-database cleanup
hit a Windows file lock. Closing Django database connections resolved cleanup;
the subsequent complete browser run exited successfully. Visual QA also corrected
CDN heading overrides, select padding, separator encoding, and currency formatting.

## Scope of confidence

This evidence supports a local academic portfolio demonstration, not a production
certification. No concurrent multi-process load test, exhaustive security audit,
or public deployment was performed. Dependency lifecycle, SQLite concurrency,
payment/return simulation, reporting dates, and other actual limits are documented
in [Known Limitations](../README.md#known-limitations).
