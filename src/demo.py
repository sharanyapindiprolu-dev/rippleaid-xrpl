import xrpl
import hashlib

# XRPL Testnet JSON-RPC
client = xrpl.clients.JsonRpcClient("https://s.altnet.rippletest.net:51234")


def account_link(addr: str) -> str:
    return f"https://testnet.xrpl.org/accounts/{addr}"


def print_result(label: str, resp):
    # resp.result['meta']['TransactionResult'] is the simplest success/fail indicator
    result = resp.result.get("meta", {}).get("TransactionResult")
    tx_hash = resp.result.get("hash")
    print(f"{label}: {result}")
    if tx_hash:
        print(f"Tx: https://testnet.xrpl.org/transactions/{tx_hash}")


print("Connecting to XRPL Testnet...")

# 1) Create & fund 4 wallets on XRPL Testnet
def create_wallet(name: str):
    wallet = xrpl.wallet.generate_faucet_wallet(client)
    print(f"{name} address: {wallet.classic_address}")
    print(f"Explorer: {account_link(wallet.classic_address)}")
    return wallet


ngo = create_wallet("NGO (Issuer)")
beneficiary = create_wallet("Beneficiary")
merchant = create_wallet("Merchant")
attacker = create_wallet("Attacker")

print("\n--- XRPL Wallets created and funded ---\n")

# 2) Beneficiary sets DID (keep it SHORT: 'data' must be <= 256 chars)
proof_hash = hashlib.sha256(b"mock-kyc").hexdigest()
did_data_str = f"v1|verified|{proof_hash}"  # short string

did_tx = xrpl.models.transactions.DIDSet(
    account=beneficiary.classic_address,
    data=did_data_str.encode().hex(),  # DIDSet wants HEX
)
did_resp = xrpl.transaction.submit_and_wait(did_tx, client, beneficiary)
print_result("DIDSet result", did_resp)

# 3) NGO sets issuer flags:
# - DefaultRipple (8) helps issued token transfers between non-issuer accounts (beneficiary -> merchant)
# - RequireAuth (2) enables Authorized Trust Lines (allowlist)
#
# We use numeric flags to avoid enum name differences across xrpl-py versions.
#
# asfDefaultRipple = 8
# asfRequireAuth   = 2

issuer_default_ripple_tx = xrpl.models.transactions.AccountSet(
    account=ngo.classic_address,
    set_flag=8,
)
resp = xrpl.transaction.submit_and_wait(issuer_default_ripple_tx, client, ngo)
print_result("NGO set DefaultRipple", resp)

issuer_require_auth_tx = xrpl.models.transactions.AccountSet(
    account=ngo.classic_address,
    set_flag=2,
)
resp = xrpl.transaction.submit_and_wait(issuer_require_auth_tx, client, ngo)
print_result("NGO set RequireAuth", resp)

print("\nNGO: RequireAuth enabled (Authorized Trust Lines mode)\n")

# 4) Beneficiary + Merchant create trust lines (FOD/MED) to NGO issuer
def create_trustline(holder_wallet, issuer_wallet, currency: str, limit: str = "1000"):
    tx = xrpl.models.transactions.TrustSet(
        account=holder_wallet.classic_address,
        limit_amount=xrpl.models.amounts.IssuedCurrencyAmount(
            currency=currency,
            issuer=issuer_wallet.classic_address,
            value=limit,
        ),
    )
    r = xrpl.transaction.submit_and_wait(tx, client, holder_wallet)
    print_result(f"TrustLine created ({holder_wallet.classic_address[:6]}.. {currency})", r)


for cur in ["FOD", "MED"]:
    create_trustline(beneficiary, ngo, cur)
    create_trustline(merchant, ngo, cur)

print("\nBeneficiary + Merchant trust lines created.\n")

# 5) NGO authorizes those trust lines (allowlist) using tfSetfAuth = 0x00010000
def authorize_trustline(issuer_wallet, user_wallet, currency: str):
    tx = xrpl.models.transactions.TrustSet(
        account=issuer_wallet.classic_address,
        # In issuer->user TrustSet for auth, LimitAmount.issuer = user's address, value = "0"
        limit_amount=xrpl.models.amounts.IssuedCurrencyAmount(
            currency=currency,
            issuer=user_wallet.classic_address,
            value="0",
        ),
        flags=0x00010000,  # tfSetfAuth
    )
    r = xrpl.transaction.submit_and_wait(tx, client, issuer_wallet)
    print_result(f"NGO authorized {currency} for {user_wallet.classic_address[:6]}..", r)


for cur in ["FOD", "MED"]:
    authorize_trustline(ngo, beneficiary, cur)
    authorize_trustline(ngo, merchant, cur)

print("\nAuthorized trust lines for verified users.\n")

# 6) Payment helper
def pay_xrp(sender_wallet, dest_wallet, xrp_amount: float, label: str):
    tx = xrpl.models.transactions.Payment(
        account=sender_wallet.classic_address,
        destination=dest_wallet.classic_address,
        amount=str(xrpl.utils.xrp_to_drops(xrp_amount)),
    )
    r = xrpl.transaction.submit_and_wait(tx, client, sender_wallet)
    print_result(label, r)
    return r


def pay_token(sender_wallet, dest_wallet, currency: str, value: str, issuer_wallet, label: str):
    amt = xrpl.models.amounts.IssuedCurrencyAmount(
        currency=currency,
        issuer=issuer_wallet.classic_address,
        value=str(value),
    )
    tx = xrpl.models.transactions.Payment(
        account=sender_wallet.classic_address,
        destination=dest_wallet.classic_address,
        amount=amt,
    )
    r = xrpl.transaction.submit_and_wait(tx, client, sender_wallet)
    print_result(label, r)
    return r


# 7) NGO issues vouchers to Beneficiary
pay_token(ngo, beneficiary, "FOD", "50", ngo, "NGO -> Beneficiary: 50 FOD")
pay_token(ngo, beneficiary, "MED", "20", ngo, "NGO -> Beneficiary: 20 MED")

# 8) Beneficiary spends vouchers at Merchant
pay_token(beneficiary, merchant, "FOD", "10", ngo, "Beneficiary -> Merchant: 10 FOD")

# 9) Merchant redeems vouchers back to NGO
pay_token(merchant, ngo, "FOD", "10", ngo, "Merchant -> NGO: redeem 10 FOD")

# 10) NGO settles Merchant in XRP
pay_xrp(ngo, merchant, 5, "NGO -> Merchant: settle 5 XRP")

# 11) Attacker test: attacker creates trustline but is NOT authorized; NGO tries to send FOD -> should fail
print("\n--- Attacker test (should FAIL due to RequireAuth) ---")
create_trustline(attacker, ngo, "FOD")

try:
    pay_token(ngo, attacker, "FOD", "1", ngo, "NGO -> Attacker: 1 FOD (should FAIL)")
except Exception as e:
    print("Expected failure (RequireAuth). Error:")
    print(str(e)[:200])

print("\nDemo complete.")
print("Tip: open the Explorer links printed above during your screen recording to show audit trail.")
