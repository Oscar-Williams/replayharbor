import json
import urllib.error
import pytest
from replayharbor.settings import Settings
from replayharbor.deepseek import probe, NoRedirect, ProviderError


def test_probe_safe_output_and_bounds(monkeypatch):
    requests=[]
    class Reply:
        def __init__(self,data):self.data=data
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):return json.dumps(self.data).encode()
    class Opener:
        def open(self,req,timeout):
            requests.append(req)
            if req.data is None:return Reply({'data':[{'id':'deepseek-flash'}]})
            return Reply({'choices':[{'message':{'content':'private echo'}}],'usage':{'total_tokens':20}})
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:Opener())
    key='sk-'+'y'*32
    result=probe(Settings(key,'https://api.deepseek.com','deepseek-flash'),True)
    assert key not in str(result) and 'private echo' not in str(result)
    assert result['completion_called'] and len(requests)==2
    assert json.loads(requests[1].data)['max_tokens']==16
    assert NoRedirect().redirect_request(None,None,302,'',{},'https://example.com') is None


def test_http_error_suppressed(monkeypatch):
    class Opener:
        def open(self,req,timeout):raise urllib.error.HTTPError(req.full_url,401,'private error',{},None)
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:Opener())
    with pytest.raises(ProviderError) as exc:
        probe(Settings('sk-'+'y'*32,'https://api.deepseek.com','deepseek-flash'))
    assert '401' in str(exc.value) and 'private error' not in str(exc.value)
