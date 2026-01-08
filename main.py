from xrpl.wallet import Wallet

# Create a new XRP wallet (beneficiary wallet)
wallet = Wallet.create()
print(f"Address: {wallet.classic_address}")
print(f"Secret: {wallet.seed}")
