from flask import Flask, request, jsonify
from flask_cors import CORS
from cdmn import DMNEngine
import json
import hashlib
import time
import os
import re
import requests
from dotenv import load_dotenv
from web3 import Web3
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# DMN Engine instance
dmn_engine = DMNEngine()

# In-memory cache for DMN results
cache = {}
latest_cache_key = None
cache_by_hash = {}
latest_request_id = None

OCR_LISTENER_ENABLED = os.getenv('OCR_LISTENER_ENABLED', 'true').lower() in ['1', 'true', 'yes']
OCR_RPC_URL = os.getenv('OCR_RPC_URL', 'http://localhost:8545')
OCR_AGGREGATOR_ADDRESS = os.getenv('OCR_AGGREGATOR_ADDRESS', '').strip()
OCR_POLL_INTERVAL = float(os.getenv('OCR_POLL_INTERVAL', '2'))
FIREFLY_CORE_URL = os.getenv('FIREFLY_CORE_URL', '').strip().rstrip('/')
IPFS_GATEWAY_URL = os.getenv('IPFS_GATEWAY_URL', '').strip().rstrip('/')
DMN_FETCH_TIMEOUT = int(os.getenv('DMN_FETCH_TIMEOUT', '15'))


class CachedResult:
    def __init__(self, request_id, decision_id, value, raw, hash_hex, hash_dec):
        self.request_id = request_id
        self.decision_id = decision_id
        self.value = value
        self.raw = raw
        self.hash_hex = hash_hex
        self.hash_dec = hash_dec
        self.updated_at = int(time.time() * 1000)


@app.route('/api/dmn/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time() * 1000),
        "service": "CDMN Decision Engine",
        "version": "1.0.0"
    })


@app.route('/api/dmn/evaluate', methods=['POST'])
def evaluate_decision():
    """Evaluate DMN decision endpoint"""
    try:
        data = request.get_json()
        dmn_content = resolve_dmn_content(data)
        decision_id = data.get('decisionId')
        input_data = normalize_input_data(data.get('inputData'))

        if not all([dmn_content, decision_id, input_data]):
            return jsonify({
                "success": False,
                "error": "缺少必要参数：dmnContent/dmnCid, decisionId 或 inputData"
            }), 400

        app.logger.info(f"正在执行决策: {decision_id}")
        app.logger.info(f"输入数据: {input_data}")

        # Evaluate decision
        result = dmn_engine.evaluate(dmn_content, decision_id, input_data)

        app.logger.info(f"决策结果: {result}")

        return jsonify({
            "success": True,
            "result": result,
            "decisionId": decision_id,
            "timestamp": int(time.time() * 1000)
        })

    except Exception as e:
        app.logger.error(f"执行决策时出错: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        }), 500


@app.route('/api/dmn/calc', methods=['POST'])
def calc_and_cache():
    """Calculate and cache DMN result endpoint"""
    try:
        data = request.get_json()
        request_id = normalize_request_id(data.get('requestId'))
        dmn_content = resolve_dmn_content(data)
        decision_id = data.get('decisionId')
        input_data = normalize_input_data(data.get('inputData'))

        if not all([dmn_content, decision_id, input_data]):
            return jsonify({
                "ok": False,
                "error": "缺少必要参数：dmnContent/dmnCid, decisionId 或 inputData"
            }), 400

        # Evaluate decision
        result = dmn_engine.evaluate(dmn_content, decision_id, input_data)
        raw = json.dumps(result)
        hash_hex = calculate_sha3_hash(raw)
        hash_dec = int(hash_hex, 16) & ((1 << 128) - 1)
        hash_dec_str = str(hash_dec)

        # Store in cache
        cached = CachedResult(request_id, decision_id, result, raw, hash_hex, hash_dec_str)
        global latest_cache_key, latest_request_id
        cache_key = f"{request_id}:{decision_id}" if request_id else str(time.time())
        cache[cache_key] = cached
        if cached.hash_hex:
            cache_by_hash[cached.hash_hex.lower()] = cached
        if cached.hash_dec is not None:
            cache_by_hash[str(cached.hash_dec)] = cached
        if request_id:
            if latest_request_id is None or request_id != latest_request_id:
                latest_cache_key = cache_key
                latest_request_id = request_id
        else:
            latest_cache_key = cache_key

        return jsonify({
            "ok": True,
            "requestId": request_id,
            "value": result,
            "raw": raw,
            "hash": hash_hex,
            "hashDec": hash_dec_str,
            "updatedAt": cached.updated_at
        })

    except Exception as e:
        app.logger.error(f"计算和缓存决策结果时出错: {str(e)}")
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.route('/api/dmn/latest', methods=['GET'])
def get_latest():
    """Get latest cached result endpoint"""
    require_ready = request.args.get('requireReady')

    if latest_cache_key is None or latest_cache_key not in cache:
        response = {
            "ok": True,
            "ready": False,
            "value": 0,
            "hashDec": 0,
            "requestId": None,
            "updatedAt": 0
        }
        if require_ready in ['1', 'true', 'True']:
            return jsonify(response), 409
        return jsonify(response), 404

    cached = cache[latest_cache_key]
    return jsonify({
        "ok": True,
        "ready": True,
        "value": cached.value,
        "raw": cached.raw,
        "hash": cached.hash_hex,
        "hashDec": cached.hash_dec,
        "requestId": cached.request_id,
        "updatedAt": cached.updated_at
    })


@app.route('/api/dmn/by-hash', methods=['GET'])
def get_by_hash():
    """Get result by hash endpoint"""
    hash_param = request.args.get('hash')
    app.logger.info(f"DMN /by-hash request hash={hash_param}")

    hash_param_lower = hash_param.lower() if hash_param else ""

    cached = cache_by_hash.get(hash_param_lower) or cache_by_hash.get(str(hash_param))
    if cached:
        return jsonify({
            "ok": True,
            "raw": cached.raw,
            "hash": cached.hash_hex,
            "hashDec": cached.hash_dec,
            "requestId": cached.request_id,
            "updatedAt": cached.updated_at
        })

    for cached in cache.values():
        if (cached.hash_hex and cached.hash_hex.lower() == hash_param_lower) or \
           (cached.hash_dec and str(cached.hash_dec) == str(hash_param)):
            return jsonify({
                "ok": True,
                "raw": cached.raw,
                "hash": cached.hash_hex,
                "hashDec": cached.hash_dec,
                "requestId": cached.request_id,
                "updatedAt": cached.updated_at
            })

    return jsonify({
        "ok": False,
        "error": "not found"
    })


@app.route('/api/dmn/ack', methods=['POST'])
def ack_and_clear():
    """Acknowledge and clear cache endpoint"""
    data = request.get_json()
    request_id = normalize_request_id(data.get('requestId'))
    block_timestamp_ms = normalize_long(data.get('blockTimestampMs'))
    result = ack_and_clear_cache(request_id, block_timestamp_ms)
    return jsonify({"ok": True, **result})


def ack_and_clear_cache(request_id=None, block_timestamp_ms=None):
    """Clear cache by requestId or block timestamp"""
    global latest_cache_key, latest_request_id

    cleared_latest = False
    removed_by_request_id = False
    skipped_latest = False

    app.logger.info(f"ACK received: requestId={request_id}, blockTimestampMs={block_timestamp_ms}")

    if request_id:
        keys_to_remove = [k for k, v in cache.items() if v.request_id == request_id]
        for key in keys_to_remove:
            cached = cache.get(key)
            if cached:
                if cached.hash_hex:
                    cache_by_hash.pop(cached.hash_hex.lower(), None)
                if cached.hash_dec is not None:
                    cache_by_hash.pop(str(cached.hash_dec), None)
            del cache[key]
            if key == latest_cache_key:
                cleared_latest = True
        removed_by_request_id = len(keys_to_remove) > 0
    elif block_timestamp_ms:
        if latest_cache_key and latest_cache_key in cache:
            cached = cache[latest_cache_key]
            if cached.updated_at > block_timestamp_ms:
                skipped_latest = True
            else:
                if cached.hash_hex:
                    cache_by_hash.pop(cached.hash_hex.lower(), None)
                if cached.hash_dec is not None:
                    cache_by_hash.pop(str(cached.hash_dec), None)
                del cache[latest_cache_key]
                cleared_latest = True

    if cleared_latest:
        latest_cache_key = None
        latest_request_id = None
        if cache:
            sorted_cache = sorted(cache.items(), key=lambda x: x[1].updated_at, reverse=True)
            latest_cache_key = sorted_cache[0][0]
            latest_request_id = sorted_cache[0][1].request_id

    app.logger.info(
        f"ACK result: clearedLatest={cleared_latest}, skippedLatest={skipped_latest}, removedByRequestId={removed_by_request_id}"
    )

    return {
        "clearedLatest": cleared_latest,
        "removedByRequestId": removed_by_request_id,
        "skippedLatest": skipped_latest
    }


@app.route('/api/dmn/input-info', methods=['POST'])
def get_input_info():
    """Get DMN input info endpoint"""
    try:
        data = request.get_json()
        dmn_content = resolve_dmn_content(data)

        if not dmn_content:
            return jsonify({
                "success": False,
                "error": "缺少必要参数：dmnContent 或 dmnCid"
            }), 400

        input_info = dmn_engine.get_input_info(dmn_content)

        return jsonify({
            "success": True,
            "inputs": input_info,
            "timestamp": int(time.time() * 1000)
        })

    except Exception as e:
        app.logger.error(f"获取决策信息时出错: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        }), 500


def normalize_input_data(input_data):
    """Normalize input data"""
    if input_data is None:
        return None
    if isinstance(input_data, dict):
        return input_data
    if isinstance(input_data, str):
        raw = input_data.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            repaired = repair_loose_json(raw)
            if repaired and repaired != raw:
                try:
                    app.logger.warning(
                        "normalize_input_data repaired non-standard JSON inputData: %s -> %s",
                        raw,
                        repaired
                    )
                    return json.loads(repaired)
                except Exception:
                    return None
            return None
    return None


def repair_loose_json(raw):
    """Repair simple JS-like object literals into valid JSON.

    Supported examples:
    - {numberOfUnits:1,urgent:false}
    - {applicant:{age:20}}
    """
    if not isinstance(raw, str):
        return None
    candidate = raw.strip()
    if not candidate.startswith("{") or not candidate.endswith("}"):
        return candidate

    # Quote unquoted object keys after "{" or ",".
    candidate = re.sub(
        r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:',
        r'\1"\2":',
        candidate
    )
    return candidate


def is_inline_dmn(value):
    if value is None:
        return False
    raw = str(value).strip()
    return raw.startswith("<") and "<definitions" in raw


def looks_like_ipfs_cid(value):
    if value is None:
        return False
    raw = str(value).strip()
    return raw.startswith("Qm") or raw.startswith("bafy")


def extract_cid_from_blob_public(public_url):
    if not public_url:
        return None
    match = re.search(r"/ipfs/([^/?#]+)", str(public_url))
    if match:
        return match.group(1)
    return None


def fetch_json(url):
    response = requests.get(url, timeout=DMN_FETCH_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_text(url):
    response = requests.get(url, timeout=DMN_FETCH_TIMEOUT)
    response.raise_for_status()
    return response.text


def fetch_dmn_via_firefly(data_id):
    if not FIREFLY_CORE_URL:
        return None

    data_url = f"{FIREFLY_CORE_URL}/api/v1/namespaces/default/data/{data_id}"
    app.logger.info(f"Resolving DMN via FireFly data record: {data_url}")
    payload = fetch_json(data_url)
    blob = payload.get("blob") or {}
    public_url = blob.get("public")
    if public_url:
        return fetch_text(public_url)

    cid = extract_cid_from_blob_public(public_url) or blob.get("hash")
    if cid and IPFS_GATEWAY_URL:
        return fetch_text(f"{IPFS_GATEWAY_URL}/{cid}")
    return None


def fetch_dmn_via_ipfs(cid):
    if not IPFS_GATEWAY_URL:
        return None
    url = f"{IPFS_GATEWAY_URL}/{cid}"
    app.logger.info(f"Resolving DMN via IPFS gateway: {url}")
    return fetch_text(url)


def resolve_dmn_content(data):
    if not isinstance(data, dict):
        return None

    dmn_content = data.get('dmnContent')
    if is_inline_dmn(dmn_content):
        return str(dmn_content)
    if dmn_content and not data.get('dmnCid'):
        return dmn_content

    dmn_cid = data.get('dmnCid')
    if is_inline_dmn(dmn_cid):
        return str(dmn_cid)
    if not dmn_cid:
        return None

    errors = []
    if looks_like_ipfs_cid(dmn_cid):
        try:
            content = fetch_dmn_via_ipfs(str(dmn_cid).strip())
            if content:
                return content
        except Exception as exc:
            errors.append(f"ipfs: {exc}")

    try:
        content = fetch_dmn_via_firefly(str(dmn_cid).strip())
        if content:
            return content
    except Exception as exc:
        errors.append(f"firefly: {exc}")

    if not looks_like_ipfs_cid(dmn_cid):
        try:
            content = fetch_dmn_via_ipfs(str(dmn_cid).strip())
            if content:
                return content
        except Exception as exc:
            errors.append(f"ipfs-fallback: {exc}")

    raise Exception(
        f"无法解析 DMN 内容: dmnCid={dmn_cid}, errors={'; '.join(errors) if errors else 'none'}"
    )


def normalize_request_id(request_id):
    """Normalize request id"""
    if request_id is None:
        return None
    raw = str(request_id).strip()
    if not raw:
        return None
    if raw.startswith("0x") and len(raw) == 66:
        return raw.lower()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            inner = raw[1:-1].strip()
            if not inner:
                return None
            parts = [p.strip() for p in inner.split(",") if p.strip() != ""]
            if len(parts) != 32:
                return raw
            b = bytes((int(p) % 256 for p in parts))
            return "0x" + b.hex()
        except Exception:
            return raw
    return raw


def normalize_long(value):
    """Normalize long value"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return None


def calculate_sha3_hash(data):
    """Calculate SHA3-256 hash of data"""
    # Use keccak256 to match Solidity keccak256(bytes(raw))
    digest = Web3.keccak(text=data).hex()
    return "0x" + digest

def start_ocr_listener():
    if not OCR_LISTENER_ENABLED:
        app.logger.info("OCR listener disabled by config")
        return
    if not OCR_AGGREGATOR_ADDRESS:
        app.logger.warning("OCR listener disabled: aggregator address is empty")
        return
    try:
        w3 = Web3(Web3.HTTPProvider(OCR_RPC_URL))
        if not w3.is_connected():
            app.logger.error("OCR listener failed: cannot connect to RPC")
            return
        try:
            checksum_addr = Web3.to_checksum_address(OCR_AGGREGATOR_ADDRESS)
        except Exception as e:
            app.logger.error(f"OCR listener failed: invalid aggregator address {OCR_AGGREGATOR_ADDRESS}: {str(e)}")
            return
        topic = Web3.keccak(text="NewTransmission(uint32,int192,address,int192[],bytes,bytes32)").hex()
        if not topic.startswith("0x"):
            topic = "0x" + topic
        log_filter = w3.eth.filter({'address': checksum_addr, 'topics': [topic]})
        app.logger.info(f"OCR listener enabled (RPC={OCR_RPC_URL}, aggregator={checksum_addr})")
        while True:
            for log in log_filter.get_new_entries():
                block_number = log.get('blockNumber')
                try:
                    block = w3.eth.get_block(block_number)
                    ts_ms = int(block.timestamp) * 1000
                except Exception:
                    ts_ms = None
                app.logger.info(f"OCR NewTransmission log received: block={block_number}, ts_ms={ts_ms}")
                ack_result = ack_and_clear_cache(block_timestamp_ms=ts_ms)
                app.logger.info(f"OCR ack result: {ack_result}")
            time.sleep(OCR_POLL_INTERVAL)
    except Exception as e:
        app.logger.error(f"OCR listener error: {str(e)}")

def run_ocr_listener():
    t = threading.Thread(target=start_ocr_listener, daemon=True)
    t.start()


if __name__ == '__main__':
    run_ocr_listener()
    app.run(
        host=os.getenv('FLASK_RUN_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_RUN_PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
