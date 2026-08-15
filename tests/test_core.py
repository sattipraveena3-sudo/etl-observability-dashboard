from app.core import Store,check_quality,detect_schema_drift,simulate
def test_drift():
    assert detect_schema_drift({'id':'int'},{'id':'string','new':'float'})=={'added':['new'],'removed':[],'changed':['id']}
def test_quality():
    q=check_quality(100,90,10,0,100); assert 'null_rate' in q.breached
def test_alerts(tmp_path):
    s=Store(tmp_path/'x.db'); simulate(s,15); assert s.rows('runs') and s.rows('alerts')
