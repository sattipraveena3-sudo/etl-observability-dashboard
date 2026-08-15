import json, random, sqlite3, time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class QualityResult:
    null_rate: float; duplicate_rate: float; row_delta: float; breached: list[str]

def detect_schema_drift(baseline:dict,current:dict)->dict:
    return {"added":sorted(current.keys()-baseline.keys()),"removed":sorted(baseline.keys()-current.keys()),"changed":sorted(k for k in baseline.keys()&current.keys() if baseline[k]!=current[k])}

def check_quality(rows_in:int,rows_out:int,nulls:int,duplicates:int,historical_average:float)->QualityResult:
    null_rate=nulls/max(rows_out,1); duplicate_rate=duplicates/max(rows_out,1); row_delta=abs(rows_out-historical_average)/max(historical_average,1)
    breached=[]
    if null_rate>.08: breached.append("null_rate")
    if duplicate_rate>.04: breached.append("duplicate_rate")
    if row_delta>.35: breached.append("row_count")
    return QualityResult(null_rate,duplicate_rate,row_delta,breached)

class Store:
    def __init__(self,path="data/metrics.db"):
        Path(path).parent.mkdir(parents=True,exist_ok=True); self.path=path; self.setup()
    def connect(self): return sqlite3.connect(self.path)
    def setup(self):
        with self.connect() as c:
            c.execute("create table if not exists runs(id integer primary key,job text,status text,duration real,rows_in int,rows_out int,null_rate real,duplicate_rate real,schema_json text,created real)")
            c.execute("create table if not exists alerts(id integer primary key,job text,level text,message text,created real)")
    def add_run(self,run):
        with self.connect() as c: c.execute("insert into runs(job,status,duration,rows_in,rows_out,null_rate,duplicate_rate,schema_json,created) values(?,?,?,?,?,?,?,?,?)",run)
    def alert(self,job,level,message):
        with self.connect() as c: c.execute("insert into alerts(job,level,message,created) values(?,?,?,?)",(job,level,message,time.time()))
    def rows(self,table):
        with self.connect() as c:
            c.row_factory=sqlite3.Row; return [dict(x) for x in c.execute(f"select * from {table} order by id desc limit 200")]

def simulate(store:Store,count=24,seed=7):
    rng=random.Random(seed); baseline={"id":"int","value":"float","source":"string"}
    for i in range(count):
        job=["orders_etl","customer_dimensions","events_rollup"][i%3]; status="failed" if i%13==0 else "success"; rows_in=rng.randint(8000,12000); rows_out=int(rows_in*rng.uniform(.82,.99)); nulls=int(rows_out*(.13 if i%9==0 else rng.uniform(.005,.025))); dup=int(rows_out*(.07 if i%11==0 else rng.uniform(0,.015))); schema=baseline|({"campaign":"string"} if i%8==0 else {})
        q=check_quality(rows_in,rows_out,nulls,dup,10000); duration=rng.uniform(30,90)*(2.8 if i%7==0 else 1)
        store.add_run((job,status,duration,rows_in,rows_out,q.null_rate,q.duplicate_rate,json.dumps(schema),time.time()+i))
        drift=detect_schema_drift(baseline,schema)
        if status=="failed": store.alert(job,"critical","job execution failed")
        if q.breached: store.alert(job,"warning","quality breach: "+", ".join(q.breached))
        if any(drift.values()): store.alert(job,"warning","schema drift: "+json.dumps(drift))
