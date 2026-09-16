from __future__ import annotations
import json
from database import reset_db
from guest_longitudinal import build_guest_los_signal
from hypotheses import create_hypotheses, apply_evidence
from actions import generate_guest_capacity_alternatives
from employee import record_shift_observation, build_employee_pressure_signal
from signals import add_signal_evidence, refresh_signal_state


def seed(path='setds_demo.db'):
    conn=reset_db(path)
    conn.execute('INSERT INTO guests VALUES (?,?,?,?)',('G-104','2028-06-01',json.dumps(['repeat']),'Illustrative demo guest'))
    visits=[
        ('V-2028-104','G-104','2028-07-10','2028-07-16',6,json.dumps(['spa','breakfast']),480000,'direct'),
        ('V-2029-104','G-104','2029-07-12','2029-07-15',3,json.dumps(['breakfast']),210000,'direct'),
        ('V-2030-104','G-104','2030-07-14','2030-07-16',2,json.dumps(['breakfast']),160000,'direct'),
    ]
    conn.executemany('INSERT INTO visits VALUES (?,?,?,?,?,?,?,?)',visits)
    conn.executemany('INSERT INTO feedback VALUES (?,?,?,?,?,?,?,?)',[
        ('F-2028-104','V-2028-104','G-104',9,'Excellent stay; spa was great.',0.7,0.9,'2028-07-17'),
        ('F-2029-104','V-2029-104','G-104',7,'Wanted spa, but no convenient slots.',0.2,0.6,'2029-07-16'),
        ('F-2030-104','V-2030-104','G-104',7,'Short trip again; spa timing still inconvenient.',0.1,0.5,'2030-07-17'),
    ])
    conn.commit()
    sid=build_guest_los_signal(conn,'G-104',{'length_of_stay'})
    add_signal_evidence(conn,sid,'targeted_question_confirms','F-2030-104','corroborates','Guest-reported')
    refresh_signal_state(conn,sid,{'length_of_stay'})
    create_hypotheses(conn,sid,{
        'H1':('price sensitivity',0.25),
        'H2':('changed personal context',0.25),
        'H3':('spa capacity / schedule mismatch',0.25),
        'H4':('competitor pull',0.25),
    })
    apply_evidence(conn,sid,'targeted_question_confirms',{'H1':0.4,'H2':0.4,'H3':2.0,'H4':1.0},'F-2030-104','Guest-reported')
    apply_evidence(conn,sid,'operational_data_confirms',{'H3':1.8},'capacity-log-demo','Observed')
    action_ids=generate_guest_capacity_alternatives(conn,'H3')
    conn.execute('INSERT INTO employees VALUES (?,?,?)',('E-01','front desk','Illustrative demo employee'))
    record_shift_observation(conn,'E-01','2030-07-10','front desk',8,0,30,12,18,2,2,0,4,3,2,'Observed')
    record_shift_observation(conn,'E-01','2030-07-11','front desk',11,180,66,31,35,1,2,5,0,18,5,'Observed')
    emp_sid=build_employee_pressure_signal(conn,'E-01',{'staff_load'})
    return conn,sid,action_ids,emp_sid

if __name__=='__main__':
    seed(); print('Demo database seeded.')
