import io
import json
import re
import threading
import time
import urllib.request
import urllib.error
import zipfile
import pytest
from replayharbor.workbench import make_server, validate_job, is_cancelled
from replayharbor.validation import confirm_candidate, compare_revision
from replayharbor.core import Config, diagnose


def test_cancelled_validation_preserves_empty_evidence():
    report=diagnose(2,lambda k,s:bool(k),Config(8,'uniform'))
    assert confirm_candidate(report,lambda k,s:bool(k),n=10,budget=20,cancelled=lambda:True)['status']=='cancelled'
    assert compare_revision(lambda k,s:True,lambda k,s:False,1,n=10,budget=20,cancelled=lambda:True)['status']=='cancelled'
    assert is_cancelled({'confirmation':{'status':'cancelled'}})


@pytest.mark.parametrize('body',[{'task':'x','budget':True},{'task':'x','budget':65},{'task':'x','confirm':'yes'},{'task':'x','repair':'unknown'},{'task':'x','path':'.env'}])
def test_input_boundary(body):
    with pytest.raises(ValueError):validate_job(body,{'x':{'repairs':[]}})


def test_http_workflow_and_boundaries(tmp_path):
    server=make_server(tmp_path,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    def request(path,body=None,headers=None):
        data=None if body is None else json.dumps(body).encode()
        return urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers or {}),timeout=5)
    try:
        page=request('/').read().decode()
        token=re.search(r'name="csrf-token" content="([^"]+)"',page).group(1)
        with pytest.raises(urllib.error.HTTPError) as e:request('/.env')
        assert e.value.code==404
        with pytest.raises(urllib.error.HTTPError) as e:request('/api/jobs',{})
        assert e.value.code==403
        headers={'X-ReplayHarbor-Token':token,'Origin':base}
        with pytest.raises(urllib.error.HTTPError) as e:request('/api/jobs',{},dict(headers,Origin='https://example.com'))
        assert e.value.code==403
        job=json.load(request('/api/jobs',{'task':'calendar_missing_timezone','budget':12},headers))
        for _ in range(100):
            state=json.load(request('/api/jobs/'+job['id']))
            if state['status']!='running':break
            time.sleep(.01)
        assert state['status']=='completed'
        assert state['report']['attempts']==12
        raw=request('/api/jobs/'+job['id']+'/bundle').read()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert 'report.json' in archive.namelist()
            assert not any('.env' in name for name in archive.namelist())
    finally:
        server.shutdown();server.server_close();thread.join()
