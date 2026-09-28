"""Bounded official-endpoint probe. No raw requests, responses or keys are logged."""
import json
import re
import urllib.request
import urllib.error


class ProviderError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request(settings, path, payload=None):
    headers = settings.auth_headers()
    headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(settings.base_url+path,
                                    data=None if payload is None else json.dumps(payload).encode(),
                                    headers=headers)
    # Avoid forwarding Authorization through redirects or ambient proxy configuration.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(1024*1024+1)
        if len(raw)>1024*1024:
            raise ProviderError('response exceeded probe limit')
        return json.loads(raw)
    except urllib.error.HTTPError as error:
        raise ProviderError(f'DeepSeek HTTP {error.code}; response body suppressed') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderError('DeepSeek connection failed; no request details logged') from None
    except (ValueError, UnicodeError):
        raise ProviderError('DeepSeek returned an invalid response') from None


def probe(settings, completion=False):
    data = _request(settings, '/models')
    models = [m.get('id','') for m in data.get('data',[]) if isinstance(m,dict)]
    ids = [m for m in models if isinstance(m,str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',m)]
    result = dict(authentication='passed', model=settings.model,
                  configured_model_available=settings.model in ids, completion_called=False)
    if completion:
        if settings.model not in ids:
            raise ProviderError('configured model is absent from the authenticated model list')
        response = _request(settings,'/chat/completions',dict(
            model=settings.model, messages=[dict(role='user',content='Reply with the word OK only.')],
            max_tokens=16, stream=False, thinking={'type':'disabled'}))
        content = response.get('choices',[{}])[0].get('message',{}).get('content','')
        usage = response.get('usage',{})
        result.update(completion_called=True, nonempty_response=isinstance(content,str) and bool(content.strip()),
                      usage={k:v for k,v in usage.items() if k in {
                          'prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens',
                          'prompt_cache_miss_tokens'} and type(v) is int})
    return result
