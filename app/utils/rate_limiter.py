import time
from flask import request
from flask import jsonify
from ..session import r


def rate_limit(length: int):
    ip = request.remote_addr

    # If an ip address is not recieved throw an error
    if not ip:
        return jsonify({"error": "Rate limited Unable to process request address"}), 429

    # Check if the user has made more than the required amounts of requests within 10 seconds
    timestamp = time.time()
    values = r.zrangebyscore(ip, timestamp, "+inf")

    if len(values) > length:
        return jsonify({"error": "Rate limited too many requests"}), 429

    # Stores the time the requests were made to the ip address that made the request
    ttl_seconds = 10
    expire_at = time.time() + ttl_seconds
    r.zadd(ip, {f"request{timestamp}": expire_at})

    # Removes expired requests
    r.zremrangebyscore(ip, "-inf", timestamp)
