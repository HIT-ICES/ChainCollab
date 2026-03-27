#!/usr/bin/env python3
"""
Simple test script for CDMN Python Server
"""

import requests
import json
import time


class CDMNServerTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url

    def test_health(self):
        """Test health check endpoint"""
        print("Testing health check...")
        url = f"{self.base_url}/api/dmn/health"

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check successful: {data['status']}")
                print(f"   Service: {data['service']}")
                print(f"   Version: {data['version']}")
                return True
            else:
                print(f"❌ Health check failed with status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check failed with exception: {str(e)}")
            return False

    def test_evaluate(self, dmn_content, decision_id, input_data):
        """Test decision evaluation endpoint"""
        print(f"Testing evaluate endpoint for decision '{decision_id}'...")
        url = f"{self.base_url}/api/dmn/evaluate"

        payload = {
            "dmnContent": dmn_content,
            "decisionId": decision_id,
            "inputData": input_data
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Evaluate successful")
                print(f"   Decision ID: {data.get('decisionId')}")
                print(f"   Result: {json.dumps(data.get('result'), indent=2)}")
                return True
            else:
                error_msg = response.json().get('error', str(response.text))
                print(f"❌ Evaluate failed with status {response.status_code}: {error_msg}")
                return False
        except Exception as e:
            print(f"❌ Evaluate failed with exception: {str(e)}")
            return False

    def test_calc_cache(self, dmn_content, decision_id, input_data, request_id=None):
        """Test calculate and cache endpoint"""
        print(f"Testing calc endpoint for decision '{decision_id}'...")
        url = f"{self.base_url}/api/dmn/calc"

        payload = {
            "requestId": request_id,
            "dmnContent": dmn_content,
            "decisionId": decision_id,
            "inputData": input_data
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Calc successful")
                print(f"   Request ID: {data.get('requestId')}")
                print(f"   Result: {json.dumps(data.get('value'), indent=2)}")
                print(f"   Hash: {data.get('hash')}")
                print(f"   HashDec: {data.get('hashDec')}")
                return True, data
            else:
                error_msg = response.json().get('error', str(response.text))
                print(f"❌ Calc failed with status {response.status_code}: {error_msg}")
                return False, None
        except Exception as e:
            print(f"❌ Calc failed with exception: {str(e)}")
            return False, None

    def test_get_latest(self):
        """Test get latest result endpoint"""
        print("Testing get latest endpoint...")
        url = f"{self.base_url}/api/dmn/latest"

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Get latest successful")
                print(f"   Ready: {data.get('ready')}")
                if data.get('ready'):
                    print(f"   Result: {json.dumps(data.get('value'), indent=2)}")
                    print(f"   Hash: {data.get('hash')}")
                    print(f"   HashDec: {data.get('hashDec')}")
                return True, data
            elif response.status_code == 404:
                print(f"ℹ️ No data in cache")
                return True, None
            else:
                print(f"❌ Get latest failed with status: {response.status_code}")
                return False, None
        except Exception as e:
            print(f"❌ Get latest failed with exception: {str(e)}")
            return False, None

    def test_get_by_hash(self, hash_hex):
        """Test get by hash endpoint"""
        print(f"Testing get by hash endpoint for hash '{hash_hex}'...")
        url = f"{self.base_url}/api/dmn/by-hash"

        params = {
            "hash": hash_hex
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    print(f"✅ Get by hash successful")
                    print(f"   Raw: {data.get('raw')}")
                    print(f"   HashDec: {data.get('hashDec')}")
                    return True
                else:
                    print(f"ℹ️ Result not found for hash: {hash_hex}")
                    return True
            else:
                print(f"❌ Get by hash failed with status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get by hash failed with exception: {str(e)}")
            return False

    def test_ack_clear(self, request_id=None, block_timestamp_ms=None):
        """Test acknowledge and clear endpoint"""
        print("Testing ack and clear endpoint...")
        url = f"{self.base_url}/api/dmn/ack"

        payload = {}
        if request_id:
            payload["requestId"] = request_id
        if block_timestamp_ms:
            payload["blockTimestampMs"] = block_timestamp_ms

        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Ack successful")
                print(f"   Cleared latest: {data.get('clearedLatest')}")
                print(f"   Removed by request id: {data.get('removedByRequestId')}")
                return True, data
            else:
                print(f"❌ Ack failed with status: {response.status_code}")
                return False, None
        except Exception as e:
            print(f"❌ Ack failed with exception: {str(e)}")
            return False, None

    def test_input_info(self, dmn_content):
        """Test input info endpoint"""
        print("Testing input info endpoint...")
        url = f"{self.base_url}/api/dmn/input-info"

        payload = {
            "dmnContent": dmn_content
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Input info successful")
                if data.get('inputs'):
                    for input_info in data.get('inputs'):
                        print(f"   - {input_info.get('name')} ({input_info.get('typeRef')})")
                return True, data
            else:
                error_msg = response.json().get('error', str(response.text))
                print(f"❌ Input info failed with status {response.status_code}: {error_msg}")
                return False, None
        except Exception as e:
            print(f"❌ Input info failed with exception: {str(e)}")
            return False, None


# Example DMN for testing
EXAMPLE_DMN = """<?xml version="1.0" encoding="UTF-8"?>
<definitions id="definitions"
             name="Example"
             namespace="http://example.org"
             xmlns="http://www.omg.org/spec/DMN/20191111/MODEL/">
    <decision id="decideDiscount" name="Decide Discount">
        <decisionLogic>
            <decisionTable id="discountTable">
                <input id="input1" name="Customer Type" typeRef="string">
                    <inputExpression typeRef="string">
                        <text>customerType</text>
                    </inputExpression>
                </input>
                <input id="input2" name="Purchase Amount" typeRef="number">
                    <inputExpression typeRef="number">
                        <text>purchaseAmount</text>
                    </inputExpression>
                </input>
                <output id="output1" name="Discount" typeRef="number" />
                <rule id="rule1">
                    <inputEntry>
                        <text>"new"</text>
                    </inputEntry>
                    <inputEntry>
                        <text>>=100</text>
                    </inputEntry>
                    <outputEntry>
                        <text>10</text>
                    </outputEntry>
                </rule>
                <rule id="rule2">
                    <inputEntry>
                        <text>"regular"</text>
                    </inputEntry>
                    <inputEntry>
                        <text>>=200</text>
                    </inputEntry>
                    <outputEntry>
                        <text>15</text>
                    </outputEntry>
                </rule>
                <rule id="rule3">
                    <inputEntry>
                        <text>"vip"</text>
                    </inputEntry>
                    <inputEntry>
                        <text>>=100</text>
                    </inputEntry>
                    <outputEntry>
                        <text>20</text>
                    </outputEntry>
                </rule>
            </decisionTable>
        </decisionLogic>
    </decision>
</definitions>
"""


def main():
    print("=== CDMN Python Server Test ===")
    print()

    # Create test instance
    test = CDMNServerTest()

    # Test health check
    if not test.test_health():
        print("\nCould not connect to server. Is it running?")
        return

    print()

    # Test input info
    test.test_input_info(EXAMPLE_DMN)

    print()

    # Test evaluate
    test.test_evaluate(EXAMPLE_DMN, "decideDiscount", {
        "customerType": "vip",
        "purchaseAmount": 150
    })

    print()

    # Test calc and cache
    success, calc_result = test.test_calc_cache(EXAMPLE_DMN, "decideDiscount", {
        "customerType": "regular",
        "purchaseAmount": 250
    }, request_id="test-123")

    print()

    # Test get latest
    if success:
        test.test_get_latest()

    print()

    # Test get by hash
    if success and calc_result:
        test.test_get_by_hash(calc_result.get('hash'))

    print()

    # Test ack and clear
    if success:
        test.test_ack_clear(request_id="test-123")

    print()

    # Test get latest again
    test.test_get_latest()


if __name__ == "__main__":
    main()
