#!/usr/bin/env python3
"""
Test script for CDMN Python Server using the DMN from test-dmn-ocr.js
"""

import requests
import json
import time


class CDMNOCRTest:
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

    def test_calc_and_cache(self, dmn_content, decision_id, input_data, request_id=None):
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


# DMN content from test-dmn-ocr.js
DMN_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/DMN/20151101/dmn.xsd"
             id="dish-decision"
             name="Dish Decision"
             namespace="http://camunda.org/schema/1.0/dmn">
  <decision id="dish" name="Dish">
    <decisionTable id="decisionTable">
      <input id="input1" label="Temperature">
        <inputExpression id="expr1" typeRef="integer">
          <text>temperature</text>
        </inputExpression>
      </input>
      <input id="input2" label="Day Type">
        <inputExpression id="expr2" typeRef="string">
          <text>dayType</text>
        </inputExpression>
      </input>
      <output id="output1" label="Dish" typeRef="string" name="result"/>

      <rule id="rule1">
        <inputEntry id="entry1">
          <text>&lt; 10</text>
        </inputEntry>
        <inputEntry id="entry2">
          <text>"Weekday"</text>
        </inputEntry>
        <outputEntry id="entry3">
          <text>"Soup"</text>
        </outputEntry>
      </rule>

      <rule id="rule2">
        <inputEntry id="entry4">
          <text>&gt; 20</text>
        </inputEntry>
        <inputEntry id="entry5">
          <text>"Weekday"</text>
        </inputEntry>
        <outputEntry id="entry6">
          <text>"Salad"</text>
        </outputEntry>
      </rule>

      <rule id="rule3">
        <inputEntry id="entry7">
          <text>[11..20]</text>
        </inputEntry>
        <inputEntry id="entry8">
          <text>"Weekday"</text>
        </inputEntry>
        <outputEntry id="entry10">
          <text>"Pasta"</text>
        </outputEntry>
      </rule>

      <rule id="rule4">
        <inputEntry id="entry11">
          <text>&lt; 10</text>
        </inputEntry>
        <inputEntry id="entry12">
          <text>"Weekend"</text>
        </inputEntry>
        <outputEntry id="entry13">
          <text>"Roast"</text>
        </outputEntry>
      </rule>

      <rule id="rule5">
        <inputEntry id="entry14">
          <text>&gt; 20</text>
        </inputEntry>
        <inputEntry id="entry15">
          <text>"Weekend"</text>
        </inputEntry>
        <outputEntry id="entry16">
          <text>"Light Salad"</text>
        </outputEntry>
      </rule>
    </decisionTable>
  </decision>
</definitions>
"""


def main():
    print("=== CDMN Python Server - DMN OCR Test ===")
    print()

    # Create test instance
    test = CDMNOCRTest()

    # Test health check
    if not test.test_health():
        print("\nCould not connect to server. Is it running?")
        return

    print()

    # Test case 1: Temperature < 10, Weekday
    print("--- Test Case 1: Temperature < 10, Weekday ---")
    success1, result1 = test.test_calc_and_cache(
        DMN_CONTENT,
        "dish",
        {"temperature": 8, "dayType": "Weekday"},
        request_id="test-1"
    )

    print()

    # Test case 2: Temperature > 20, Weekend
    print("--- Test Case 2: Temperature > 20, Weekend ---")
    success2, result2 = test.test_calc_and_cache(
        DMN_CONTENT,
        "dish",
        {"temperature": 25, "dayType": "Weekend"},
        request_id="test-2"
    )

    print()

    # Test case 3: Temperature between 11-20, Weekday
    print("--- Test Case 3: Temperature 15, Weekday ---")
    success3, result3 = test.test_calc_and_cache(
        DMN_CONTENT,
        "dish",
        {"temperature": 15, "dayType": "Weekday"},
        request_id="test-3"
    )

    print()

    # Test get latest
    print("--- Testing Get Latest ---")
    test.test_get_latest()

    print()

    # Test get by hash
    if success1 and result1:
        print("--- Testing Get by Hash ---")
        test.test_get_by_hash(result1.get('hash'))

    print()

    print("=== Test Summary ===")
    print(f"Test Case 1 (Temp <10, Weekday): {'✅ Passed' if success1 else '❌ Failed'}")
    print(f"Test Case 2 (Temp >20, Weekend): {'✅ Passed' if success2 else '❌ Failed'}")
    print(f"Test Case 3 (Temp 15, Weekday): {'✅ Passed' if success3 else '❌ Failed'}")


if __name__ == "__main__":
    main()
