# Category-aware inventory design

## Canonical shop categories

- Kirana
- Stationery
- Pharmacy
- Doctor Prescription
- Dairy
- Hardware
- Fast Food
- General
- Clothing
- Other

`Stationary`, `Medical`, `Doctor`, and `Restaurant` remain accepted as legacy
input aliases. The API stores and returns the canonical names above.

## Inventory isolation

The application uses a secure logical inventory database for each
`(owner_id, shop_category)` pair. This is stronger and safer than exposing a
client-selected database/table name:

- the authenticated user's current profile category determines the scope;
- the client cannot submit a category with an item request;
- list, create, update, delete, voice inventory, voice billing, bulk embeds,
  and RAG vector retrieval all filter by that scope;
- changing a profile from Kirana to Hardware reveals the Hardware inventory;
  the Kirana records remain stored but inaccessible until the user switches
  back;
- update and delete return `404` for a record in another category, so the API
  does not reveal whether it exists.

Bills, sales analytics, dashboard totals, and the profile remain shared per
user as requested. A bill and its sale rows also retain an immutable snapshot
of the active category at the time of sale. The Dashboard deliberately
aggregates every category, while RAG analytics filters that snapshot before
adding sales information to an AI prompt. Billing only uses the active
category's inventory to map a product name to its product group, avoiding
cross-category product context.

## Deployment

For an existing Supabase database, run these SQL files once in the Supabase
SQL editor before deployment:

- `backend_app/db/migrations/20260807_category_scoped_inventory.sql`
- `backend_app/db/migrations/20260807_category_scoped_sales_context.sql`

The backend also includes one-time startup compatibility checks, but the
checked-in SQL migrations are the preferred operational record.

New installations get the `items.shop_category` column and its indexes from
the SQLModel definition.

## Frontend layout structure

`frontend_app/lib/features/category_experience/` owns category page metadata
and the category page factory. Every retail category reuses the existing Voice
page (including its voice-input circle) and loads its category-specific
inventory groups:

| Shop category | Category pages | Shared pages |
| --- | --- | --- |
| Kirana | Voice, Inventory, Frequent Billing | Dashboard, Profile |
| Fast Food | Voice, Inventory, Frequent Billing | Dashboard, Profile |
| Dairy | Voice, Inventory, Frequent Billing | Dashboard, Profile |
| Hardware, Stationery, Pharmacy, General, Clothing, Other | Voice, Inventory | Dashboard, Profile |
| Doctor Prescription | Voice, Patient History, Past Records | Profile |

Doctor Prescription's Patient History and Past Records are layout-only in this
release. They deliberately make no clinical-data request and display no
patient data until consent, role-based access, audit logging, and retention
rules have been implemented. The first Doctor page uses the exact same Voice
screen as Kirana.

The frequent-billing shortcut state is held separately per shop category in
the Flutter shell. Switching a profile category clears the previous
category's in-progress frequent bill and never exposes its shortcuts in the
new category.
