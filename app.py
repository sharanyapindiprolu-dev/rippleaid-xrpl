import streamlit as st
import subprocess
import sys

st.set_page_config(page_title="RippleAid+ Demo", layout="centered")

st.title("RippleAid+ — Verified Aid Vouchers (XRPL Testnet)")
st.write("Runs the end-to-end XRPL demo (DIDSet + RequireAuth + TrustLines + Issued Tokens + Payments).")

if st.button("Run XRPL Demo"):
    st.info("Running... funding wallets + submitting transactions can take 1–2 minutes.")
    p = subprocess.run([sys.executable, "-u", "src/demo.py"], capture_output=True, text=True)

    if p.returncode == 0:
        st.success("Demo complete ✅")
        st.code(p.stdout)
    else:
        st.error("Demo failed ❌")
        st.code(p.stdout + "\n" + p.stderr)
