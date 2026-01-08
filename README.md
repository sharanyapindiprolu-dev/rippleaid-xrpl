# RippleAid+ — Verified Aid Vouchers on XRPL (DID + Authorized Trust Lines)

**Tagline:** Aid vouchers that only verified recipients can use, with instant merchant settlement and a full audit trail on XRPL.

## Problem
In disaster relief (shelters/camps), aid delivery breaks down because:
- Duplicate/fake claims happen (re-registration, missing IDs)
- Paper vouchers/cash are slow and leak-prone
- Merchants hesitate if redemption/settlement is delayed
- NGOs struggle to reconcile distributions and redemptions across locations

## Solution (What RippleAid+ does)
RippleAid+ issues **aid voucher tokens** that **only verified wallets can hold**.
Beneficiaries spend vouchers at merchants, merchants redeem back to the NGO, and NGOs settle merchants in XRP.
Every step is recorded on XRPL Testnet for transparency and auditability.

## XRPL Features Used (and how we used them)
1) **DIDSet**
- Beneficiary writes a **non-PII** DID record (demo stores a short proof hash)

2) **Issued Tokens + Trust Lines (TrustSet)**
- NGO is the issuer
- Voucher tokens (issued currencies):
  - `FOD` = food voucher token
  - `MED` = medical voucher token
- Beneficiary + Merchant create trust lines to the issuer

3) **Authorized Trust Lines (RequireAuth)**
- NGO enables **RequireAuth** to enforce allowlisted trust lines
- NGO explicitly authorizes beneficiary + merchant trust lines
- Unverified wallets cannot receive voucher tokens

4) **Payments**
- NGO distributes voucher tokens to beneficiary
- Beneficiary pays merchant using voucher tokens
- Merchant redeems voucher tokens back to NGO
- NGO settles merchant in **XRP**

## Demo Flow (what `src/demo.py` proves)
1. Creates & funds 4 wallets on XRPL Testnet:
   - NGO (issuer), Beneficiary, Merchant, Attacker
2. Beneficiary sets DID (non-PII proof)
3. NGO enables RequireAuth + DefaultRipple
4. Beneficiary & Merchant create trust lines for `FOD` and `MED`
5. NGO authorizes those trust lines (verified allowlist)
6. NGO issues vouchers to Beneficiary
7. Beneficiary spends vouchers at Merchant
8. Merchant redeems vouchers back to NGO
9. NGO settles Merchant in XRP
10. Attacker tries to receive vouchers and fails (enforcement works)

## How to Run (XRPL Testnet)

## How to Run (XRPL Testnet)

### Install dependencies
```bash
pip install -r requirements.txt
