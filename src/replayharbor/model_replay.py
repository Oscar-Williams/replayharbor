"""Real DeepSeek inference over a restorable, synthetic Delta-MFP environment."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from .adapter import verify_upstream, UPSTREAM_SHA
from .deepseek import _request, ProviderError
from .export_guard import assert_publishable
from .core import Config, diagnose


class BudgetExceeded(RuntimeError):
    pass


class BoundedModel:
    """Single-flight client with conservative per-call reservation and no retry."""
    def __init__(self, settings, max_calls=24, cap_usd=0.10):
        if type(max_calls) is not int or not 1 <= max_calls <= 24 or not 0 < cap_usd <= .10:
            raise ValueError('smoke run is limited to 24 calls and USD 0.10')
        if settings.model != 'deepseek-flash':
            raise ValueError('this rate card is scoped to deepseek-flash')
        self.settings, self.max_calls, self.cap_usd = settings, max_calls, cap_usd
        self.entries=[]
        self.charged_estimate=0.0

    def complete(self, prompt):
        assert_publishable(prompt)
        prompt_bytes=len(prompt.encode('utf-8'))
        if prompt_bytes>10000:
            raise BudgetExceeded('prompt exceeds the smoke-run input limit')
        # One byte per token plus 1024 chat-format overhead is a conservative estimate,
        # not an exact provider tokenizer. Peak uncached prices, verified 2026-09-28.
        reserved=((prompt_bytes+1024)*.30 + 192*1.20)/1_000_000
        if len(self.entries)>=self.max_calls or self.charged_estimate+reserved>self.cap_usd:
            raise BudgetExceeded('model call or cost reservation limit reached')
        entry=dict(call=len(self.entries)+1, reserved_usd=reserved, status='reserved')
        self.entries.append(entry)
        self.charged_estimate+=reserved
        response=_request(self.settings,'/chat/completions',dict(
            model=self.settings.model, messages=[dict(role='user',content=prompt)],
            max_tokens=192, temperature=0.2, stream=False, thinking={'type':'disabled'}))
        try:
            content=response['choices'][0]['message']['content']
            usage=response['usage']
            inp,out=usage['prompt_tokens'],usage['completion_tokens']
            if not isinstance(content,str) or type(inp) is not int or type(out) is not int or min(inp,out)<0:
                raise ValueError()
        except (KeyError,IndexError,TypeError,ValueError):
            entry['status']='invalid_response_reservation_retained'
            raise ProviderError('invalid model response; reservation retained') from None
        cost=(inp*.30+out*1.20)/1_000_000
        entry.update(status='completed',prompt_tokens=inp,completion_tokens=out,estimated_usd=cost)
        self.charged_estimate+=cost-reserved
        if cost>reserved:
            self.max_calls=len(self.entries)
            raise BudgetExceeded('observed usage exceeded reservation; further calls disabled')
        assert_publishable(content)
        return content

    def public_ledger(self):
        return dict(calls=len(self.entries),max_calls=self.max_calls,cap_usd=self.cap_usd,
                    estimated_usd=self.charged_estimate,entries=self.entries,
                    price_source='https://api-docs.deepseek.com/quick_start/pricing/',
                    price_date='2026-09-28',pricing='peak uncached upper estimate; actual billing may be lower')


def build_model_prompt(task, history, task_contract='original-v1'):
    from agents.interfaces import TOOL_DOCS
    tools={name:TOOL_DOCS.get(name,'Ask a clarification using kind=clarify.') for name in task.tools}
    # Exclude evaluator effects, fault labels, correct plans and metadata answers.
    visible=[{k:row[k] for k in ('action','tool_result')} for row in history]
    if task_contract not in {'original-v1','explicit-date-v2'}:
        raise ValueError('unknown public task contract')
    context = {}
    if task_contract == 'explicit-date-v2':
        if task.task_id != 'calendar_missing_timezone':raise ValueError('task contract is scoped to the calendar smoke case')
        context = {'requested_date':'2026-05-09', 'date_format':'YYYY-MM-DD',
                   'time_format':'HH:MM', 'source':'explicit public fixture context added after interface audit'}
    return ('Complete a task in a synthetic tool environment. Return exactly one JSON object, no markdown. '
            'Forms: {"kind":"tool","tool_name":"NAME","tool_args":{...}}, '
            '{"kind":"clarify","tool_args":{"field":"FIELD"}}, '
            '{"kind":"final","final_answer":"..."}. '
            'Use tool results as evidence. Ask for missing facts. Finish after completing the task.\n'
            +json.dumps(dict(goal=task.goal,public_context=context,tools=tools,history=visible),ensure_ascii=True))


def parse_action(raw, task):
    from benchmarks.diagnostic_env import AgentAction
    try:
        obj=json.loads(raw)
        if not isinstance(obj,dict) or obj.get('kind') not in {'tool','clarify','final'}:
            raise ValueError()
        args=obj.get('tool_args',{})
        if not isinstance(args,dict):raise ValueError()
        tool=obj.get('tool_name')
        if obj['kind']=='tool' and tool not in task.tools:raise ValueError()
        if obj['kind']=='final' and not isinstance(obj.get('final_answer'),str):raise ValueError()
        return AgentAction(kind=obj['kind'],tool_name=tool,tool_args=args,final_answer=obj.get('final_answer'))
    except (ValueError,TypeError):
        raise ValueError('invalid model action schema') from None


def exact_step(task, action):
    # Evaluator-only matching; stricter than upstream's partial-argument matcher.
    for spec in task.correct_steps+task.faulty_steps:
        if spec.kind != action.kind or (spec.tool_name and spec.tool_name != action.tool_name):continue
        if all(action.tool_args.get(k)==v for k,v in spec.tool_args.items()):
            return spec
    return None


def run_episode(task, model, snapshot=None, max_steps=5, task_contract='original-v1'):
    from benchmarks.diagnostic_env import DiagnosticEnv
    if type(max_steps) is not int or not 1 <= max_steps <= 5:raise ValueError('invalid step limit')
    state=deepcopy(snapshot) if snapshot is not None else None
    env=DiagnosticEnv(task,state=state['env'] if state else None)
    history=deepcopy(state['history']) if state else []
    snapshots=[dict(env=env.snapshot(),history=deepcopy(history))]
    steps=[]
    answer=None
    status='step_limit'
    for _ in range(max_steps):
        prompt=build_model_prompt(task,history,task_contract)
        raw=model.complete(prompt)
        try:
            action=parse_action(raw,task)
        except ValueError:
            status='invalid_action'
            break
        result,_=env.execute(action,exact_step(task,action))
        row=dict(action=asdict(action),tool_result=result,
                 prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        steps.append(row)
        history.append(row)
        snapshots.append(dict(env=env.snapshot(),history=deepcopy(history)))
        if action.kind=='final':
            answer=action.final_answer
            status='final'
            break
    evaluation=env.evaluate(answer).to_dict()
    return dict(status=status,final_success=evaluation['success'],evaluation=evaluation,
                steps=steps,snapshots=snapshots)


def run_model_smoke(settings, task_contract='explicit-date-v2'):
    verify_upstream()
    from benchmarks.diagnostic_env import make_tasks
    task=next(t for t in make_tasks() if t.task_id=='calendar_missing_timezone')
    model=BoundedModel(settings)
    result=dict(schema_version=1,provenance='real_deepseek_inference_in_synthetic_environment',
                upstream_sha=UPSTREAM_SHA,model=settings.model,task_id=task.task_id,
                task_contract=task_contract,
                settings_public=settings.public_summary(),status='running',replays=[],
                inference_seed_supported=False,temperature=0.2,max_output_tokens=192,
                protocol='one baseline then three exploration rollouts; maximum five calls each',
                limits='smoke only; no independence, confidence, accuracy or repair-effect claim')
    try:
        baseline=run_episode(task,model,task_contract=task_contract)
        result['baseline']=baseline
        def replay(prefix, sample_label):
            run=run_episode(task,model,baseline['snapshots'][prefix],task_contract=task_contract)
            result['replays'].append(dict(prefix=prefix,sample_label=sample_label,run=run))
            return not run['final_success']
        result['diagnosis']=diagnose(len(baseline['snapshots']),replay,Config(3,'uniform'))
        result['status']='completed' if result['diagnosis']['error'] is None else 'partial'
    except (BudgetExceeded,ProviderError,ValueError,KeyError,TypeError) as exc:
        result.update(status='stopped',error_type=type(exc).__name__)
    finally:
        result['ledger']=model.public_ledger()
    assert_publishable(result)
    return result
