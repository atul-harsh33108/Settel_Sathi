# SettleSaathi Synthetic Fixtures Validation Report

**Validation Status:** ✅ **PASSED**  
**Fixture Directory:** `serv_data\fixtures\v1`  
**Total Verification Checks Passed:** `107`
**Total Errors Found:** `0`  
**Total Warnings:** `0`  

## 1. Verified Invariants
- **Mathematical Balance:** Gross = Net + Fees + Taxes - Adjustments for all settlement records.
- **Settlement Arithmetic:** Settlement net equals gross minus fees/tax plus signed adjustment.
- **Referential Integrity:** All line items link directly to valid settlement IDs and source transactions.
- **Manifest Integrity:** Listed file hashes, sizes, and record counts match the bundle.
- **Schema Headers:** Core CSV headers and column order match the v1 contract.
- **Synthetic Data Safety:** Core and nested CSV/JSON fixtures scanned for phone, PAN, Aadhaar, and live Paytm endpoint patterns.
- **Hero Demo Alignment (SCN-02):** Collected ₹18,450.00, Settled ₹18,450.00, Bank credit ₹0.00.
- **Scenario Oracle Alignment:** Oracle amounts match the referenced transaction, settlement, and bank records.

## 2. Issues & Warnings
- *No blocking errors detected.*

## 3. Conclusion
This report covers fixture integrity checks only; it does not certify the product importer or reconciler.
