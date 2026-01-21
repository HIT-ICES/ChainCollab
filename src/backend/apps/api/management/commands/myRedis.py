import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0)

def setKV(key, value):
    print("SAVE KV")
    r.set(key, value)

def readKV(key):
    value = r.get(key)
    if value:
        return value.decode('utf-8')  # 将字节解码为字符串
    else:
        return None
