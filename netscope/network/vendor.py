import json
from functools import lru_cache
from netscope.utils.paths import asset
from netscope.network.system import normalize_mac


@lru_cache(maxsize=1)
def catalog():
    path=asset('oui.json')
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def lookup(mac):
    mac=normalize_mac(mac)
    if not mac or int(mac[:2],16)&3:
        return ''  # Locally administered/randomized or multicast; never claim an IEEE vendor.
    return catalog().get(mac.replace(':','')[:6],'')
