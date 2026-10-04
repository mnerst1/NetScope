import json
import sqlite3
import time
import uuid
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
 id TEXT PRIMARY KEY, ip TEXT NOT NULL, mac TEXT NOT NULL DEFAULT '', hostname TEXT NOT NULL DEFAULT '',
 name TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT 'device', tags TEXT NOT NULL DEFAULT '',
 favorite INTEGER NOT NULL DEFAULT 0, trusted INTEGER NOT NULL DEFAULT 0, vendor TEXT NOT NULL DEFAULT '',
 first_seen REAL NOT NULL, last_seen REAL NOT NULL, online INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS devices_mac ON devices(mac);
CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, device_id TEXT REFERENCES devices(id), ts REAL, online INTEGER);
CREATE INDEX IF NOT EXISTS obs_device_ts ON observations(device_id,ts);
CREATE TABLE IF NOT EXISTS latency_samples (id INTEGER PRIMARY KEY, device_id TEXT REFERENCES devices(id), ts REAL, ms REAL);
CREATE INDEX IF NOT EXISTS latency_device_ts ON latency_samples(device_id,ts);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, ts REAL, device_id TEXT, kind TEXT, detail TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, ts REAL, label TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS notes (device_id TEXT PRIMARY KEY REFERENCES devices(id), text TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS traffic (ts REAL PRIMARY KEY, interface TEXT, rx REAL, tx REAL);
PRAGMA user_version=1;
"""


class Repository:
    def __init__(self, path, mode='live'):
        if mode not in ('live','demo'):
            raise ValueError('Unsupported data mode')
        self.mode = mode
        self.path = str(path)
        with self.connect() as c:
            if c.execute("PRAGMA user_version").fetchone()[0] > 1:
                raise RuntimeError("Database belongs to a newer NetScope version")
            c.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        try:
            with c:
                yield c
        finally:
            c.close()

    def setting(self, key, default=None):
        with self.connect() as c:
            r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(r[0]) if r else default

    def set_setting(self, key, value):
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def devices(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM devices ORDER BY favorite DESC, online DESC, ip")]

    def update_device(self, device_id, **fields):
        allowed = {'name', 'kind', 'tags', 'favorite', 'trusted'}
        if not fields or not set(fields) <= allowed:
            raise ValueError("Unsupported editable field")
        with self.connect() as c:
            c.execute("UPDATE devices SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?", (*fields.values(), device_id))

    def merge_scan(self, probes, vendor=None, now=None, scope=None):
        now = now if now is not None else time.time()
        events = []
        # A stale ARP entry for an old DHCP address must not overwrite a live MAC observation.
        live_macs={p.mac for p in probes if p.online and p.mac}
        probes=[p for p in probes if p.online or not p.mac or p.mac not in live_macs]
        seen=set()
        with self.connect() as c:
            for p in probes:
                r = c.execute("SELECT * FROM devices WHERE mac=? AND mac<>''", (p.mac,)).fetchone() if p.mac else None
                if r is None:
                    candidate = c.execute("SELECT * FROM devices WHERE ip=? ORDER BY last_seen DESC LIMIT 1", (p.ip,)).fetchone()
                    # An IP with a different known MAC is a different device (DHCP address reuse).
                    if candidate and (not candidate['mac'] or not p.mac or candidate['mac'] == p.mac):
                        r = candidate
                if r is None:
                    if not p.online:
                        continue
                    did = uuid.uuid4().hex
                    c.execute("INSERT INTO devices(id,ip,mac,hostname,first_seen,last_seen,online,vendor) VALUES(?,?,?,?,?,?,?,?)",
                              (did,p.ip,p.mac,p.hostname,now,now,1,vendor(p.mac) if vendor else ''))
                    kind = 'new'
                else:
                    did = r['id']
                    kind = ('online' if p.online else 'offline') if bool(r['online']) != p.online else None
                    c.execute("UPDATE devices SET ip=?,mac=?,hostname=?,online=?,last_seen=?,vendor=? WHERE id=?",
                              (p.ip,p.mac or r['mac'],p.hostname or r['hostname'],int(p.online),now if p.online else r['last_seen'],
                               (vendor(p.mac) if vendor and p.mac else '') or r['vendor'],did))
                if did in seen:
                    continue
                seen.add(did)
                c.execute("INSERT INTO observations(device_id,ts,online) VALUES(?,?,?)", (did,now,int(p.online)))
                c.execute("INSERT INTO latency_samples(device_id,ts,ms) VALUES(?,?,?)", (did,now,p.latency))
                if kind:
                    c.execute("INSERT INTO events(ts,device_id,kind,detail) VALUES(?,?,?,?)", (now,did,kind,p.ip))
                    events.append({'kind':kind,'ip':p.ip,'id':did})
            if scope:
                import ipaddress
                net=ipaddress.ip_network(scope)
                for r in c.execute('SELECT id,ip FROM devices WHERE online=1').fetchall():
                    if r['id'] not in seen and ipaddress.ip_address(r['ip']) in net:
                        c.execute('UPDATE devices SET online=0 WHERE id=?',(r['id'],))
                        c.execute('INSERT INTO observations(device_id,ts,online) VALUES(?,?,0)',(r['id'],now))
                        c.execute('INSERT INTO latency_samples(device_id,ts,ms) VALUES(?,?,NULL)',(r['id'],now))
                        c.execute('INSERT INTO events(ts,device_id,kind,detail) VALUES(?,?,?,?)',(now,r['id'],'offline',r['ip']))
                        events.append({'kind':'offline','ip':r['ip'],'id':r['id']})
        return events

    def metrics(self):
        with self.connect() as c:
            availability={r['device_id']:r['value'] for r in c.execute('SELECT device_id,100.0*SUM(online)/COUNT(*) AS value FROM observations GROUP BY device_id')}
            latest={r['device_id']:r['ms'] for r in c.execute('SELECT l.device_id,l.ms FROM latency_samples l JOIN (SELECT device_id,MAX(id) AS id FROM latency_samples GROUP BY device_id) x ON x.id=l.id')}
        return availability,latest

    def history(self, device_id, limit=300):
        with self.connect() as c:
            rows = c.execute("SELECT l.ts,l.ms,COALESCE(o.online,0) AS online FROM latency_samples l LEFT JOIN observations o ON o.device_id=l.device_id AND o.ts=l.ts WHERE l.device_id=? ORDER BY l.ts DESC LIMIT ?",(device_id,limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def availability(self, device_id):
        with self.connect() as c:
            r = c.execute("SELECT COUNT(*),COALESCE(SUM(online),0) FROM observations WHERE device_id=?", (device_id,)).fetchone()
        return 100*r[1]/r[0] if r[0] else None

    def events(self, device_id=None, limit=500):
        with self.connect() as c:
            query = "SELECT e.*, COALESCE(NULLIF(d.name,''),NULLIF(d.hostname,''),e.detail) AS name FROM events e LEFT JOIN devices d ON d.id=e.device_id"
            args = ()
            if device_id:
                query += " WHERE e.device_id=?"
                args = (device_id,)
            return [dict(r) for r in c.execute(query+" ORDER BY e.ts DESC LIMIT ?", (*args,limit))]

    def note(self, did, value=None):
        with self.connect() as c:
            if value is not None:
                c.execute("INSERT OR REPLACE INTO notes VALUES(?,?)", (did,value))
            r = c.execute("SELECT text FROM notes WHERE device_id=?",(did,)).fetchone()
            return r[0] if r else ''

    def snapshot(self, label, now=None):
        did = uuid.uuid4().hex
        with self.connect() as c:
            c.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (did,time.time() if now is None else now,label,json.dumps(self.devices())))
        return did

    def snapshots(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM snapshots ORDER BY ts DESC")]

    def traffic(self, interface, rx, tx, now=None):
        with self.connect() as c:
            c.execute("INSERT OR REPLACE INTO traffic VALUES(?,?,?,?)",(time.time() if now is None else now,interface,rx,tx))

    def traffic_history(self, interface):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM (SELECT * FROM traffic WHERE interface=? ORDER BY ts DESC LIMIT 300) ORDER BY ts",(interface,))]

    def cleanup(self, days=30, now=None):
        cutoff = (now if now is not None else time.time()) - max(1, int(days))*86400
        with self.connect() as c:
            for table in ('observations','latency_samples','events','traffic'):
                c.execute(f"DELETE FROM {table} WHERE ts<?",(cutoff,))
            c.execute("DELETE FROM snapshots WHERE id NOT IN (SELECT id FROM snapshots ORDER BY ts DESC LIMIT 100)")

    def export_history(self):
        with self.connect() as c:
            return {table:[dict(r) for r in c.execute(f"SELECT * FROM {table}")] for table in ('devices','observations','latency_samples','events','notes')}


def compare_snapshots(a, b):
    def identity(d):
        return d.get('mac') or d['id']
    old, new = ({identity(d):d for d in rows} for rows in (a,b))
    return {'added':[new[k] for k in new.keys()-old.keys()], 'removed':[old[k] for k in old.keys()-new.keys()],
            'changed':[{'before':old[k], 'after':new[k]} for k in old.keys() & new.keys()
                       if any(old[k].get(f)!=new[k].get(f) for f in ('ip','online','name','trusted','tags','kind'))]}
