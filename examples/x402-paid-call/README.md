# x402 Paid Call Example

This is the shortest path from "I found a 402" to "I received paid JSON."

The default endpoint is `https://bitcoinsapi.com/api/v1/fees/landscape`, currently priced at `$0.005`. Your buyer wallet needs USDC on Base plus a small ETH gas balance. Never commit a private key.

## Python

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install x402 eth-account requests
$env:EVM_PRIVATE_KEY = "0x..."
$env:EVM_RPC_URL = "https://mainnet.base.org"
python examples/x402-paid-call/paid_call.py
```

## TypeScript

```powershell
npm init -y
npm install @x402/fetch @x402/core @x402/evm viem dotenv tsx
$env:EVM_PRIVATE_KEY = "0x..."
$env:EVM_RPC_URL = "https://mainnet.base.org"
npx tsx examples/x402-paid-call/paid-call.ts
```

Set `SATOSHI_X402_URL` to try a different paid endpoint.

Useful discovery checks before paying:

```powershell
curl.exe https://bitcoinsapi.com/api/v1/fees
curl.exe -i https://bitcoinsapi.com/api/v1/fees/landscape
curl.exe https://bitcoinsapi.com/.well-known/x402
```
