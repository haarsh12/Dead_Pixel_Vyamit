# Backend Requirements

## Feature Name

GST Billing Profile Details

## Purpose

Persist a shop's GST billing configuration so it is available across devices and app sessions, and can be used by future invoice generation.

## Required API

`PUT /auth/update-gst-profile`

## Expected Request Body

```json
{
  "gst_enabled": true,
  "gstin": "27ABCDE1234F1Z5",
  "business_address": "123 Market Road",
  "city": "Mumbai",
  "state": "Maharashtra",
  "place_of_supply": "Maharashtra",
  "invoice_prefix": "INV",
  "gst_calculation_mode": "cgst_sgst"
}
```

## Expected Response

```json
{
  "success": true,
  "gst_enabled": true,
  "gstin": "27ABCDE1234F1Z5",
  "business_address": "123 Market Road",
  "city": "Mumbai",
  "state": "Maharashtra",
  "place_of_supply": "Maharashtra",
  "invoice_prefix": "INV",
  "gst_calculation_mode": "cgst_sgst"
}
```

## Validation Rules

- GSTIN is required when GST billing is enabled and must be exactly 15 characters.
- Business address, city, state, and place of supply are required when GST billing is enabled.
- State and place of supply must be valid Indian States or Union Territories.
- Invoice prefix is optional; if supplied, backend should define its allowed characters and maximum length.
- `gst_calculation_mode` must be either `cgst_sgst` or `igst`.

## Database Changes

- Add GST profile fields to the shop/user profile record: enabled status, GSTIN, business address, city, state, place of supply, invoice prefix, and calculation mode.
- Ensure GSTIN is stored securely and associated with the authenticated shop owner.

## Future Notes

- The Flutter implementation currently stores these values only in session memory through `GstProfileProvider`; it makes no API requests and performs no GST calculations.
- A future authenticated `GET /auth/gst-profile` endpoint is needed to hydrate the Profile screen.
- Invoice tax calculation, receipt changes, printer/PDF output, analytics, and invoice persistence remain explicitly out of scope for this phase.
