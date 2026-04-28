import { config } from "dotenv";
import { wrapFetchWithPayment } from "@x402/fetch";
import { x402Client, x402HTTPClient } from "@x402/core/client";
import { toClientEvmSigner } from "@x402/evm";
import { ExactEvmScheme, type ExactEvmSchemeOptions } from "@x402/evm/exact/client";
import { createPublicClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";

config();

const DEFAULT_URL = "https://bitcoinsapi.com/api/v1/fees/landscape";
const DEFAULT_RPC_URL = "https://mainnet.base.org";
const USER_AGENT = "SatoshiExampleX402Buyer/1.0";

const privateKey = process.env.EVM_PRIVATE_KEY;
if (!privateKey) {
  throw new Error("Set EVM_PRIVATE_KEY to a Base wallet with USDC and ETH for gas.");
}

const url = process.env.SATOSHI_X402_URL ?? DEFAULT_URL;
const rpcUrl = process.env.EVM_RPC_URL ?? DEFAULT_RPC_URL;
const account = privateKeyToAccount(privateKey as `0x${string}`);
const publicClient = createPublicClient({
  chain: base,
  transport: http(rpcUrl),
});
const evmSigner = toClientEvmSigner(account, publicClient);
const schemeOptions: ExactEvmSchemeOptions = { rpcUrl };
const client = new x402Client().register(
  "eip155:*",
  new ExactEvmScheme(evmSigner, schemeOptions),
);
const fetchWithPayment = wrapFetchWithPayment(fetch, client);

const response = await fetchWithPayment(url, {
  method: "GET",
  headers: {
    "User-Agent": USER_AGENT,
  },
});

const contentType = response.headers.get("content-type") ?? "";
const body = contentType.includes("application/json")
  ? await response.json()
  : await response.text();
const paymentResponse = new x402HTTPClient(client).getPaymentSettleResponse((name) =>
  response.headers.get(name),
);

console.log(
  JSON.stringify(
    {
      status_code: response.status,
      url,
      paid: Boolean(paymentResponse),
      payment_response: paymentResponse,
      body,
    },
    null,
    2,
  ),
);

if (!response.ok) {
  process.exit(1);
}
