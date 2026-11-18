# Rate limit (30 req/min/IP) on public search — run alone; it blocks the search for ~1 minute
import os
import pytest
import requests
from test_public_search import BASE_URL, UA, SEARCH


@pytest.mark.skipif(not os.environ.get("RUN_RATELIMIT"), reason="set RUN_RATELIMIT=1")
def test_rate_limit_429():
    s = requests.Session(); s.headers.update(UA)
    codes = [s.get(SEARCH, params={"product": "zzzzqqq"}).status_code for _ in range(32)]
    print(codes)
    assert 429 in codes
