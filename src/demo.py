import xrpl
import json
import time
import hashlib

# Connect to XRPL Testnet
client = xrpl.clients.JsonRpcClient("https://s.altnet.rippletest.net:51234")

# Helper to print account links
def link(addr):
    return f"https://testnet.xrpl.org/accounts/{addr}"

print("Connecting to XRPL Testnet...")

# 1. Create 4 test wallets
def create_wallet(name):
    wallet = xrpl.wallet.generate_faucet_wallet(client)
    print(f"{name} address:", wallet.classic_address)
    print(f"Explorer:", link(wallet.classic_address))
    return wallet

ngo = create_wallet("NGO")
beneficiary = create_wallet("Beneficiary")
merchant = create_wallet("Merchant")
attacker = create_wallet("Attacker")

print("\n--- XRPL Wallets created and funded ---\n")

# 2. Beneficiary sets DID (no personal data)
did_data = {
    "verified": True,
    "verifier": "RippleAid NGO Demo",
    "proof_hash": hashlib.sha256(b"mock-kyc").hexdigest(),
}
tx = xrpl.models.transactions.DIDSet(
    account=beneficiary.classic_address,
    data=json.dumps(did_data).encode().hex(),
)
response = xrpl.transaction.submit_and_wait(tx, client, beneficiary)
print("DIDSet result:", response.result.get("meta", {}).get("TransactionResult"))

# 3. NGO enables RequireAuth (Authorized Trust Lines)
tx = xrpl.models.transactions.AccountSet(
    account=ngo.classic_address,
    set_flag=xrpl.models.transactions.AccountSetFlag.ASF_REQUIRE_AUTH,
)
xrpl.transaction.submit_and_wait(tx, client, ngo)
print("NGO: RequireAuth enabled\n")

# 4. Create trust lines
def trust(wallet, issuer, currency):
    tx = xrpl.models.transactions.TrustSet(
        account=wallet.classic_address,
        limit_amount=xrpl.models.amounts.IssuedCurrencyAmount(
            currency=currency, issuer=issuer.classic_address, value="1000"
        ),
    )
    xrpl.transaction.submit_and_wait(tx, client, wallet)

for cur in ["FOOD", "MED"]:
    trust(beneficiary, ngo, cur)
    trust(merchant, ngo, cur)
print("Beneficiary + Merchant trust lines created.\n")

# 5. NGO authorizes trust lines (allowlist)
def authorize(issuer, user, currency):
    tx = xrpl.models.transactions.TrustSet(
        account=issuer.classic_address,
        limit_amount=xrpl.models.amounts.IssuedCurrencyAmount(
            currency=currency, issuer=user.classic_address, value="0"
        ),
        flags=0x00010000,  # tfSetfAuth
    )
    xrpl.transaction.submit_and_wait(tx, client, issuer)

for cur in ["FOOD", "MED"]:
    authorize(ngo, beneficiary, cur)
    authorize(ngo, merchant, cur)
print("Authorized trust lines for verified users.\n")

# 6. NGO issues vouchers
def pay(sender, dest, amount, currency=None, issuer=None):
    if currency:
        amt = xrpl.models.amounts.IssuedCurrencyAmount(
            currency=currency, issuer=issuer.classic_address, value=str(amount)
        )
    else:
        amt = str(xrpl.utils.xrp_to_drops(amount))
    tx = xrpl.models.transactions.Payment(
        account=sender.classic_address, amount=amt, destination=dest.classic_address
    )
    resp = xrpl.transaction.submit_and_wait(tx, client, sender)
    print(f"Payment {amount} {currency or 'XRP'} result:",
          resp.result.get('meta', {}).get('TransactionResult'))

pay(ngo, beneficiary, 50, "FOOD", ngo)
pay(ngo, beneficiary, 20, "MED", ngo)

# 7. Beneficiary pays Merchant 10 FOOD
pay(beneficiary, merchant, 10, "FOOD", ngo)

# 8. Merchant redeems 10 FOOD back to NGO
pay(merchant, ngo, 10, "FOOD", ngo)

# 9. NGO settles Merchant in 5 XRP
pay(ngo, merchant, 5)

# 10. Attempt attacker payment (should fail)
print("\nAttempting unauthorized payment to attacker...")
tx = xrpl.models.transactions.TrustSet(
    account=attacker.classic_address,
    limit_amount=xrpl.models.amounts.IssuedCurrencyAmount(
        currency="FOOD", issuer=ngo.classic_address, value="1000"
    ),
)
xrpl.transaction.submit_and_wait(tx, client, attacker)

try:
    pay(ngo, attacker, 1, "FOOD", ngo)
except Exception as e:
    print("Expected failure (RequireAuth):", str(e)[:120])

print("\n✅ Demo complete.")
