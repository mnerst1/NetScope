import html
from datetime import datetime


def history_rows(data,demo=False):
    devices={d['id']:d for d in data['devices']}
    samples={(s['device_id'],s['ts']):s['ms'] for s in data['latency_samples']}
    rows=[]
    for o in data['observations']:
        d=devices[o['device_id']]
        rows.append({'mode':'DEMO' if demo else 'LIVE','timestamp':datetime.fromtimestamp(o['ts']).isoformat(),
                     'device_id':d['id'],'current_ip':d['ip'],'mac':d['mac'],'name':d['name'] or d['hostname'],
                     'online':o['online'],'latency_ms':samples.get((d['id'],o['ts']))})
    return rows


def html_report(path,repo,demo,title,headers,status):
    esc=lambda x:html.escape(str(x))
    rows=[]
    for d in repo.devices():
        availability=repo.availability(d['id'])
        values=[d['name'] or d['hostname'],d['ip'],status['online' if d['online'] else 'offline'],
                status['trusted' if d['trusted'] else 'unknown'],f'{availability:.1f}%' if availability is not None else '—']
        rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    page='<!doctype html><meta charset="utf-8"><title>NetScope</title><style>body{font:16px Segoe UI,sans-serif;background:#f3f5fa;color:#18243a;margin:48px}table{border-collapse:collapse;width:100%;background:white}th,td{text-align:start;padding:14px;border-bottom:1px solid #dce3ef}h1{color:#346ad2}</style>'
    page+='<h1>NetScope • '+esc(title)+(' • DEMO' if demo else '')+'</h1><p>'+esc(datetime.now().isoformat(timespec='seconds'))+'</p>'
    page+='<table><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr>'+''.join(rows)+'</table>'
    with open(path,'w',encoding='utf-8') as f:
        f.write(page)
