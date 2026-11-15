import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core import Engine, warmup, llm_health
from stt import Speech, STTUnavailable, MAX_BYTES

ROOT=Path(__file__).resolve().parent
engine=Engine(str(ROOT/'crew_journal.sqlite3'))
speech=Speech()
ENGINE_LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def reply(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path=='/health':
            self.reply(200,{'server':'ok','stt':speech.health(),'stt_status':speech.statuses(),'llm':llm_health(),'clinical_protocol_enabled':False});return
        if self.path in ('/sources','/inventory'):
            self.reply(200,json.loads((ROOT/(self.path[1:]+'.json')).read_text(encoding='utf-8')));return
        if self.path in ('/','/demo'):
            page=ROOT/'crew-heart-check.html' if self.path=='/' and (ROOT/'crew-heart-check.html').is_file() else ROOT/'demo.html'
            body=page.read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        self.reply(404,{'error':'not_found'})
    def do_POST(self):
        if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765','http://localhost:8765'):
            self.reply(403,{'error':'origin_rejected'});return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if self.path=='/stt':
                if n>MAX_BYTES: self.reply(413,{'error':'audio_too_long'});return
                if n<=0 or n%2: self.reply(400,{'error':'invalid_pcm'});return
                lang=self.headers.get('X-Lang','')
                if lang not in ('ru','en'): self.reply(400,{'error':'invalid_language'});return
                result=speech.transcribe(self.rfile.read(n),lang)
            else:
                if not 0<n<=16000: raise ValueError('Invalid body size')
                data=json.loads(self.rfile.read(n))
                if not isinstance(data,dict): raise ValueError('Object required')
                # Serialize state mutations while keeping /health and STT responsive.
                with ENGINE_LOCK:
                    if self.path=='/session': result=engine.start(data.get('mission_context'),data.get('equipment'))
                    elif self.path=='/extract': result=engine.propose(data['session_id'],data['text'])
                    elif self.path=='/confirm': result=engine.confirm(data['session_id'],data['proposal_id'],data['facts'])
                    elif self.path=='/clarify': result=engine.clarify(data['session_id'],data['confirmation_id'],data['field'],data['value'])
                    elif self.path=='/scenario': result=engine.scenario(data['session_id'],data['confirmation_id'])
                    elif self.path=='/step': result=engine.mark_step(data['session_id'],data['plan_id'],data['step_id'])
                    elif self.path=='/export':
                        engine.require_session(data['session_id']);result={'events':engine.history(data['session_id']),'delivery_status':'local_only_not_sent'}
                    else: self.reply(404,{'error':'not_found'});return
            self.reply(200,result)
        except STTUnavailable: self.reply(503,{'error':'stt_unavailable'})
        except (ValueError,KeyError,TypeError): self.reply(400,{'error':'invalid_request'})
        except Exception: self.reply(500,{'error':'local_processing_failed'})

if __name__=='__main__':
    threading.Thread(target=warmup,daemon=True).start()
    threading.Thread(target=speech.load,daemon=True).start()
    print('Crew AI: http://127.0.0.1:8765 — startup checks running; /health shows readiness')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
