from __future__ import annotations
import sqlite3, statistics, json
from signals import record_signal, add_signal_evidence, refresh_signal_state

LOS_THRESHOLD = 0.30

def get_guest_visit_history(conn: sqlite3.Connection, guest_id: str) -> list[dict]:
    rows = conn.execute('''SELECT visit_id,start_date,end_date,length_of_stay_nights,services,price_paid,channel
    FROM visits WHERE guest_id=? ORDER BY start_date''',(guest_id,)).fetchall()
    out=[]
    for r in rows:
        d=dict(r); d['services']=json.loads(d['services'] or '[]'); out.append(d)
    return out

def calculate_visit_deviations(values: list[float]) -> list[dict]:
    out=[]
    for i,obs in enumerate(values):
        if i==0:
            out.append({'index':i,'baseline':None,'observed':obs,'deviation':None}); continue
        base=statistics.mean(values[:i]); dev=None if base==0 else (obs-base)/base
        out.append({'index':i,'baseline':base,'observed':obs,'deviation':dev})
    return out

def directional_persistence(deviations: list[dict], threshold: float=LOS_THRESHOLD) -> int:
    valid=[d['deviation'] for d in deviations if d['deviation'] is not None and abs(d['deviation'])>=threshold]
    if not valid: return 0
    last_sign=1 if valid[-1]>0 else -1; streak=0
    for dev in reversed(valid):
        if (1 if dev>0 else -1)!=last_sign: break
        streak+=1
    return streak

def latest_worsening(deviations: list[dict], threshold: float=LOS_THRESHOLD) -> bool:
    valid=[d['deviation'] for d in deviations if d['deviation'] is not None and abs(d['deviation'])>=threshold]
    return len(valid)>=2 and valid[-1]*valid[-2]>0 and abs(valid[-1])>abs(valid[-2])

def service_usage_changes(history: list[dict]) -> dict:
    if len(history)<2: return {'dropped':[],'added':[]}
    a=set(history[-2]['services']); b=set(history[-1]['services'])
    return {'dropped':sorted(a-b),'added':sorted(b-a)}

def revisit_intervals_days(history: list[dict]) -> list[int]:
    from datetime import date
    starts=[date.fromisoformat(h['start_date']) for h in history]
    return [(starts[i]-starts[i-1]).days for i in range(1,len(starts))]

def build_guest_los_signal(conn: sqlite3.Connection, guest_id: str,
                           owner_priority_set: set[str] | None=None) -> str | None:
    hist=get_guest_visit_history(conn,guest_id)
    if len(hist)<2: return None
    vals=[h['length_of_stay_nights'] for h in hist]
    devs=calculate_visit_deviations(vals); latest=devs[-1]
    if latest['deviation'] is None or abs(latest['deviation'])<LOS_THRESHOLD: return None
    persistence=directional_persistence(devs); worsening=latest_worsening(devs)
    sid=record_signal(conn,'guest','visits',hist[-1]['visit_id'],latest['baseline'],latest['observed'],latest['deviation'],
                      'length_of_stay',max(1,persistence),'down' if latest['deviation']<0 else 'up',worsening)
    add_signal_evidence(conn,sid,'guest_los_change',hist[-1]['visit_id'],'corroborates','Derived')
    ch=service_usage_changes(hist)
    if ch['dropped'] or ch['added']:
        add_signal_evidence(conn,sid,'guest_service_usage_change',hist[-1]['visit_id'],'corroborates','Derived')
    refresh_signal_state(conn,sid,owner_priority_set)
    return sid
