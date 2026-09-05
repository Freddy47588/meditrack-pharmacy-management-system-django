# Application screenshots

These images were captured from the running Django application in headless Chrome,
using a separate temporary SQLite database populated by `seed_demo`. All names,
inventory quantities, sales, and supplier contact details are demonstration data.
No database, session cookie, password, or authentication token is included.

| Image | Page |
| --- | --- |
| [Dashboard](dashboard.png) | KPIs, sales chart, top products, inventory alerts |
| [Inventory](inventory.png) | Search, pagination, stock and expiry status |
| [Cashier](kasir.png) | Product selection and estimated total before checkout |
| [Transaction](transaction-detail.png) | Completed transaction and item subtotals |
| [API documentation](api-docs.png) | Live Swagger UI |
| [Mobile dashboard](dashboard-mobile.png) | Dashboard at a 390 px viewport |

Desktop captures use a 1440 px viewport. Responsive navigation and horizontal
table scrolling were also checked at 768 px and 390 px. Full-page screenshots
can be taller than the viewport. Dates and values are snapshots of the demo;
they will differ when the seed command runs on another day.

To refresh: follow the demo setup in the root README, sign in with the demo
account using your own password, open the listed pages, and take real browser
captures. Never replace them with generated mockups or include credentials.
