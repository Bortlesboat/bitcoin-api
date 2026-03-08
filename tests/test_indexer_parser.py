"""Tests for the indexer block parser."""

import pytest
from bitcoin_api.indexer.parser import parse_block, _sat, _hex_to_bytes, ParsedBlock


def make_sample_block(*, height=100, num_txs=2, include_fee=True):
    """Create a realistic getblock verbosity=2 response."""
    txs = []

    # Coinbase tx
    coinbase_tx = {
        "txid": "cb" * 32,
        "version": 2,
        "size": 250,
        "vsize": 200,
        "weight": 800,
        "locktime": 0,
        "vin": [{"coinbase": "03640100", "sequence": 4294967295}],
        "vout": [
            {
                "value": 50.0,
                "n": 0,
                "scriptPubKey": {
                    "type": "pubkeyhash",
                    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                },
            }
        ],
    }
    txs.append(coinbase_tx)

    # Regular txs
    for i in range(1, num_txs):
        tx = {
            "txid": f"{i:02x}" * 32,
            "version": 2,
            "size": 225 + i * 10,
            "vsize": 166 + i * 5,
            "weight": 661 + i * 20,
            "locktime": 0,
            "vin": [
                {
                    "txid": f"{i+10:02x}" * 32,
                    "vout": 0,
                },
                {
                    "txid": f"{i+20:02x}" * 32,
                    "vout": 1,
                },
            ],
            "vout": [
                {
                    "value": 0.5,
                    "n": 0,
                    "scriptPubKey": {
                        "type": "witness_v0_keyhash",
                        "address": f"bc1qaddr{i}",
                    },
                },
                {
                    "value": 0.3,
                    "n": 1,
                    "scriptPubKey": {
                        "type": "witness_v1_taproot",
                        "address": f"bc1paddr{i}",
                    },
                },
            ],
        }
        if include_fee:
            tx["fee"] = 0.0001 * i
        txs.append(tx)

    return {
        "hash": "aa" * 32,
        "height": height,
        "previousblockhash": "bb" * 32,
        "time": 1700000000,
        "nTx": len(txs),
        "size": 5000,
        "weight": 15000,
        "tx": txs,
    }


# --- Tests ---

class TestSatConversion:
    def test_whole_btc(self):
        assert _sat(1.0) == 100_000_000

    def test_zero(self):
        assert _sat(0.0) == 0

    def test_small_amount(self):
        assert _sat(0.00000001) == 1

    def test_typical_output(self):
        assert _sat(0.5) == 50_000_000

    def test_coinbase_reward(self):
        assert _sat(50.0) == 5_000_000_000

    def test_precision(self):
        # Common floating-point edge case
        assert _sat(0.1 + 0.2) == 30_000_000


class TestHexToBytes:
    def test_basic(self):
        assert _hex_to_bytes("abcd") == b"\xab\xcd"

    def test_empty(self):
        assert _hex_to_bytes("") == b""

    def test_32_byte_hash(self):
        result = _hex_to_bytes("aa" * 32)
        assert len(result) == 32
        assert result == b"\xaa" * 32


class TestParseBlock:
    def test_basic_structure(self):
        block = parse_block(make_sample_block())
        assert isinstance(block, ParsedBlock)
        assert block.height == 100
        assert block.tx_count == 2
        assert len(block.transactions) == 2

    def test_block_hash(self):
        block = parse_block(make_sample_block())
        assert block.hash == bytes.fromhex("aa" * 32)
        assert block.prev_hash == bytes.fromhex("bb" * 32)

    def test_block_metadata(self):
        block = parse_block(make_sample_block())
        assert block.timestamp == 1700000000
        assert block.size == 5000
        assert block.weight == 15000

    def test_genesis_block_no_prev_hash(self):
        data = make_sample_block(height=0)
        del data["previousblockhash"]
        block = parse_block(data)
        assert block.prev_hash == bytes(32)  # 32 zero bytes

    def test_coinbase_tx(self):
        block = parse_block(make_sample_block())
        cb = block.transactions[0]
        assert cb.is_coinbase is True
        assert cb.tx_index == 0
        assert len(cb.inputs) == 0  # coinbase has no parsed inputs
        assert len(cb.outputs) == 1
        assert cb.outputs[0].value_sat == 5_000_000_000
        assert cb.outputs[0].address == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

    def test_regular_tx(self):
        block = parse_block(make_sample_block())
        tx = block.transactions[1]
        assert tx.is_coinbase is False
        assert tx.tx_index == 1
        assert len(tx.inputs) == 2
        assert len(tx.outputs) == 2

    def test_fee_extraction(self):
        block = parse_block(make_sample_block(include_fee=True))
        tx = block.transactions[1]
        assert tx.fee_sat == 10_000  # 0.0001 BTC

    def test_no_fee_field(self):
        block = parse_block(make_sample_block(include_fee=False))
        tx = block.transactions[1]
        assert tx.fee_sat is None

    def test_output_values(self):
        block = parse_block(make_sample_block())
        tx = block.transactions[1]
        assert tx.outputs[0].value_sat == 50_000_000
        assert tx.outputs[1].value_sat == 30_000_000

    def test_output_script_types(self):
        block = parse_block(make_sample_block())
        tx = block.transactions[1]
        assert tx.outputs[0].script_type == "witness_v0_keyhash"
        assert tx.outputs[1].script_type == "witness_v1_taproot"

    def test_output_addresses(self):
        block = parse_block(make_sample_block())
        tx = block.transactions[1]
        assert tx.outputs[0].address == "bc1qaddr1"
        assert tx.outputs[1].address == "bc1paddr1"

    def test_input_references(self):
        block = parse_block(make_sample_block())
        tx = block.transactions[1]
        assert tx.inputs[0].prev_txid == bytes.fromhex("0b" * 32)
        assert tx.inputs[0].prev_vout == 0
        assert tx.inputs[1].prev_txid == bytes.fromhex("15" * 32)
        assert tx.inputs[1].prev_vout == 1

    def test_op_return_output(self):
        data = make_sample_block()
        # Add an OP_RETURN output (no address)
        data["tx"][1]["vout"].append({
            "value": 0.0,
            "n": 2,
            "scriptPubKey": {
                "type": "nulldata",
                "hex": "6a0b68656c6c6f",
            },
        })
        block = parse_block(data)
        tx = block.transactions[1]
        op_return = tx.outputs[2]
        assert op_return.address is None
        assert op_return.script_type == "nulldata"
        assert op_return.value_sat == 0

    def test_many_transactions(self):
        block = parse_block(make_sample_block(num_txs=10))
        assert len(block.transactions) == 10
        for i, tx in enumerate(block.transactions):
            assert tx.tx_index == i

    def test_tx_metadata(self):
        block = parse_block(make_sample_block())
        tx = block.transactions[1]
        assert tx.version == 2
        assert tx.locktime == 0
        assert tx.size > 0
        assert tx.vsize > 0
        assert tx.weight > 0

    def test_txid_bytes(self):
        block = parse_block(make_sample_block())
        for tx in block.transactions:
            assert isinstance(tx.txid, bytes)
            assert len(tx.txid) == 32
