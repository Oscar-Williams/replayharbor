"""Loopback-only, no-key workbench. Only built-in synthetic tasks can execute."""
import io
import json
import secrets
import threading
import tempfile
import zipfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .adapter import verify_upstream
from .core import Config
from .workflow import run_workflow


def is_cancelled(report):
    return report.get('stop_reason') == 'cancelled' or any(
        report.get(stage, {}).get('status') == 'cancelled' for stage in ('confirmation', 'revision'))


def validate_job(data, cases):
    if not isinstance(data,dict) or set(data)-{'task','budget','strategy','confirm','repair'}:
        raise ValueError('请求字段不符合案例格式')
    if data.get('task') not in cases:raise ValueError('请选择内置案例')
    budget=data.get('budget',24)
    if type(budget) is not int or not 0<=budget<=64:raise ValueError('探索预算应为 0–64 次')
    strategy=data.get('strategy','uniform')
    Config(budget,strategy).validate()
    if type(data.get('confirm',False)) is not bool:raise ValueError('确认选项应为布尔值')
    repair=data.get('repair') or None
    if repair is not None and repair not in cases[data['task']]['repairs']:
        raise ValueError('该案例不支持所选修订')
    options={}
    if data.get('confirm'):options.update(confirmation_n=512,confirmation_budget=1024)
    if repair:options.update(repair_type=repair,comparison_prefix=1,comparison_n=128,comparison_budget=256)
    return Config(budget,strategy),options


def make_server(root, port=8765):
    verify_upstream()
    from benchmarks.diagnostic_env import make_tasks
    root=Path(root).resolve()
    cases={t.task_id:dict(id=t.task_id,family=t.family,goal=t.goal,repairs=list(t.repair_map)) for t in make_tasks()}
    jobs={}
    lock=threading.Lock()
    token=secrets.token_urlsafe(32)
    assets=Path(__file__).parent/'web'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def send(self,status,data,kind='application/json; charset=utf-8',attachment=None):
            raw=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,(dict,list)) else data
            self.send_response(status)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            if attachment:self.send_header('Content-Disposition',f'attachment; filename="{attachment}"')
            self.end_headers()
            self.wfile.write(raw)

        def host_ok(self):
            allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
            return self.headers.get('Host') in allowed

        def do_GET(self):
            if not self.host_ok():return self.send(403,{'error':'host rejected'})
            if self.path=='/favicon.ico':return self.send(204,b'','image/x-icon')
            if self.path=='/':
                return self.send(200,(assets/'index.html').read_text(encoding='utf-8').replace('__TOKEN__',token).encode(),'text/html; charset=utf-8')
            if self.path in {'/app.js','/style.css'}:
                return self.send(200,(assets/self.path[1:]).read_bytes(),'text/javascript' if self.path.endswith('js') else 'text/css')
            if self.path=='/api/cases':return self.send(200,list(cases.values()))
            if self.path=='/api/model-summary':
                file=root/'experiments/deepseek/summary.json'
                return self.send(200,json.loads(file.read_text()) if file.exists() else {'runs':[]})
            parts=self.path.strip('/').split('/')
            if len(parts) in {3,4} and parts[:2]==['api','jobs']:
                with lock:job=jobs.get(parts[2])
                if job is None:return self.send(404,{'error':'run not found'})
                if len(parts)==3:
                    return self.send(200,{k:v for k,v in job.items() if k!='cancel'})
                if parts[3]=='bundle' and job['status']=='completed':
                    if is_cancelled(job['report']):
                        return self.send(409,{'error':'取消记录仅供本地检查；请完成一次运行后导出可复算问题包'})
                    from .cli import write_bundle
                    # All generated temporary files stay under the project's ignored artifacts.
                    temporary=root/'artifacts/workbench-tmp'
                    temporary.mkdir(parents=True,exist_ok=True)
                    with tempfile.TemporaryDirectory(dir=temporary) as temp:
                        folder=Path(temp)/'bundle'
                        write_bundle(folder,job['task'],1,job['report'])
                        buffer=io.BytesIO()
                        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
                            for file in folder.iterdir():archive.writestr(file.name,file.read_bytes())
                    return self.send(200,buffer.getvalue(),'application/zip','replayharbor-bundle.zip')
            return self.send(404,{'error':'not found'})

        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.host_ok() or self.headers.get('X-ReplayHarbor-Token')!=token or (origin and origin!='http://'+self.headers.get('Host','')):
                return self.send(403,{'error':'request origin or token rejected'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16384:raise ValueError('请求大小超出限制')
                data=json.loads(self.rfile.read(length))
                parts=self.path.strip('/').split('/')
                if len(parts)==4 and parts[:2]==['api','jobs'] and parts[3]=='cancel':
                    with lock:job=jobs.get(parts[2])
                    if not job:return self.send(404,{'error':'run not found'})
                    job['cancel'].set()
                    return self.send(200,{'status':'cancellation_requested'})
                if self.path!='/api/jobs':return self.send(404,{'error':'not found'})
                config,options=validate_job(data,cases)
                with lock:
                    if any(j['status']=='running' for j in jobs.values()):return self.send(409,{'error':'已有运行进行中，请等待或取消'})
                    if len(jobs)>=16:jobs.pop(next(iter(jobs)))
                    run_id=secrets.token_hex(12)
                    job=dict(id=run_id,status='running',task=data['task'],cancel=threading.Event())
                    jobs[run_id]=job
                def execute():
                    try:
                        report=run_workflow(data['task'],1,config,options,job['cancel'].is_set)
                        with lock:job.update(report=report,status='completed')
                    except Exception:
                        with lock:job.update(status='error',error='运行未完成，请检查本地安装与案例条件')
                threading.Thread(target=execute,daemon=True).start()
                return self.send(202,{'id':run_id})
            except (ValueError,TypeError,KeyError):
                return self.send(400,{'error':'输入无效：请选择案例，预算范围为 0–64'})

    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def serve(root,port=8765):
    server=make_server(root,port)
    print(f'ReplayHarbor: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
