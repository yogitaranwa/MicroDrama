import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from magicdrama.audiofirst.cloud_writer import NvidiaClaudeWriter,NVIDIA_MODEL,NoOutputStall
from magicdrama.audiofirst.execution import signature

class Response:
    status_code=200
    def __init__(self,data=None,lines=()):self.data=data;self.lines=lines;self.closed=False
    def json(self):return self.data
    def raise_for_status(self):pass
    def close(self):self.closed=True
    def iter_lines(self,**kwargs):yield from self.lines


def setup(path,lines=(),clock=lambda:0,enabled=True,fallback=True):
    day=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).date().isoformat()
    c={'nvidia_model':NVIDIA_MODEL,'claude_model':'claude-sonnet-5','max_output_tokens':1000,'claude_run_cap_usd':'2.30',
       'rates_verified_on':day,'pricing_url':'https://platform.claude.com/docs/en/about-claude/pricing','input_usd_per_million':2,'output_usd_per_million':10}
    body={'model':NVIDIA_MODEL,'messages':[{'role':'system','content':'Write fiction'},{'role':'user','content':'test'}]}
    a={'run_id':'test','request_sha256':signature({'body':body,'config':c}),'approval_reference':'fixture-not-real-permission',
       'expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),'allow_claude_fallback':fallback,
       'key_identities':{'nvidia':'Saralya NVIDIA API key','claude':'Anthropic API key'}}
    class HTTP:
        def __init__(self):self.calls=[]
        def post(self,url,**kwargs):
            self.calls.append(url)
            if 'nvidia' in url:return Response(lines=lines)
            if 'count_tokens' in url:return Response({'input_tokens':20})
            return Response({'id':'msg_fixture','usage':{'input_tokens':20,'output_tokens':5},'content':[{'type':'text','text':'{}'}],'stop_reason':'end_turn'})
    h=HTTP();w=NvidiaClaudeWriter(c,a,{'nvidia':'fixture','claude':'fixture'},path,enabled,h,clock)
    return w,h,body

class CloudWriterTests(unittest.TestCase):
    def test_nvidia_first_no_paid_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            w,h,b=setup(Path(d)/'l',lines=['data: '+json.dumps({'choices':[{'delta':{'content':'{}'}}]}),'data: [DONE]'])
            self.assertEqual(w.transport(b),'{}');self.assertEqual(len(h.calls),1)
    def test_stall_then_claude_bounded_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            t=iter([0,61,61,61]);w,h,b=setup(Path(d)/'l',lines=[':keepalive'],clock=lambda:next(t,61))
            self.assertEqual(w.transport(b),'{}');self.assertIn('count_tokens',h.calls[1]);self.assertEqual(len(h.calls),3)
            with self.assertRaises(RuntimeError):w.claude(b)
            self.assertEqual(sum(u.endswith('/messages') for u in h.calls),1)
    def test_disabled_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            w,h,b=setup(Path(d)/'l',enabled=False)
            with self.assertRaises(RuntimeError):w.transport(b)
            self.assertEqual(h.calls,[])
    def test_partial_stall_does_not_pay(self):
        with tempfile.TemporaryDirectory() as d:
            t=iter([0,1,601]);w,h,b=setup(Path(d)/'l',lines=['data: '+json.dumps({'choices':[{'delta':{'content':'partial'}}]}),':ping'],clock=lambda:next(t,601))
            with self.assertRaises(TimeoutError):w.transport(b)
            self.assertEqual(len(h.calls),1)
    def test_http_error_no_paid_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            w,h,b=setup(Path(d)/'l')
            def bad(*a,**k):raise RuntimeError('HTTP 429 fixture')
            h.post=bad
            with self.assertRaises(RuntimeError):w.transport(b)
    def test_hash_rate_and_cap_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            w,h,b=setup(Path(d)/'l');b['messages'][1]['content']='changed'
            with self.assertRaises(ValueError):w.transport(b)
            w,h,b=setup(Path(d)/'l');w.config['claude_run_cap_usd']='2.31'
            w.approval['request_sha256']=signature({'body':b,'config':w.config})
            with self.assertRaises(ValueError):w.transport(b)
            w,h,b=setup(Path(d)/'l');w.config['input_usd_per_million']=999
            with self.assertRaises(ValueError):w.claude(b)
    def test_unapproved_fallback_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            w,h,b=setup(Path(d)/'l',fallback=False)
            with self.assertRaises(RuntimeError):w.claude(b)
            self.assertEqual(h.calls,[])
