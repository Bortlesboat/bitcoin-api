"""Make one paid x402 request to Satoshi API.

Prerequisites:
  pip install x402 eth-account requests

Environment:
  EVM_PRIVATE_KEY   Base wallet private key with USDC and a little ETH for gas.
  EVM_RPC_URL       Optional Base RPC URL. Defaults to https://mainnet.base.org.
  SATOSHI_X402_URL  Optional paid endpoint URL.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from eth_account import Account
from x402 import x402ClientSync
from x402.http import decode_payment_response_header
from x402.http.clients import x402_requests
from x402.mechanisms.evm import EthAccountSignerWithRPC
from x402.mechanisms.evm.exact import register_exact_evm_client


DEFAULT_URL = "https://bitcoinsapi.com/api/v1/fees/landscape"
DEFAULT_RPC_URL = "https://mainnet.base.org"
USER_AGENT = "SatoshiExampleX402Buyer/1.0"


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _response_preview(response) -> Any:
    try:
        body = response.json()
    except ValueError:
        return response.text[:500]

    if isinstance(body, dict) and isinstance(body.get("data"), dict):
        preview = dict(body)
        preview["data_keys"] = sorted(body["data"].keys())
        preview["data"] = {
            key: body["data"][key]
            for key in list(body["data"].keys())[:5]
        }
        return preview
    return body


def main() -> int:
    private_key = os.environ.get("EVM_PRIVATE_KEY")
    if not private_key:
        print(
            "Set EVM_PRIVATE_KEY to a Base wallet with USDC and ETH for gas.",
            file=sys.stderr,
        )
        return 2

    url = os.environ.get("SATOSHI_X402_URL", DEFAULT_URL)
    rpc_url = os.environ.get("EVM_RPC_URL", DEFAULT_RPC_URL)

    account = Account.from_key(private_key)
    client = x402ClientSync()
    signer = EthAccountSignerWithRPC(account, rpc_url=rpc_url)
    register_exact_evm_client(client, signer)

    session = x402_requests(client)
    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=45,
    )

    payment_header = response.headers.get("PAYMENT-RESPONSE") or response.headers.get(
        "X-PAYMENT-RESPONSE"
    )
    payment_response = (
        _to_jsonable(decode_payment_response_header(payment_header))
        if payment_header
        else None
    )

    result = {
        "status_code": response.status_code,
        "url": url,
        "paid": payment_response is not None,
        "payment_response": payment_response,
        "body": _response_preview(response),
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    response.raise_for_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
