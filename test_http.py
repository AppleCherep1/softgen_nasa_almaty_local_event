import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

class HTTPTests(unittest.TestCase):
    def test_routes_missing_models_and_audio_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f in Path(__file__).parent.glob('*.py'):shutil.copy(f,root/f.name)
            for name in ('demo.html','sources.json','inventory.json'):shutil.copy(Path(__file__).with_name(name),root/name)
            (root/'crew-heart-check.html').write_text('<h1>MAIN_INTERFACE_MARKER</h1>')
            proc=subprocess.Popen([sys.executable,str(root/'server.py')],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                for _ in range(60):
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=2) as r:health=json.load(r)
                        break
                    except OSError:time.sleep(.1)
                else:self.fail('Server did not start')
                self.assertEqual(set(health['stt']),{'ru','en'})
                self.assertEqual(set(health['llm']),{'ready','model','warm','status'})
                with urllib.request.urlopen('http://127.0.0.1:8765/') as r:self.assertIn(b'MAIN_INTERFACE_MARKER',r.read())
                with urllib.request.urlopen('http://127.0.0.1:8765/demo') as r:self.assertNotIn(b'MAIN_INTERFACE_MARKER',r.read())
                def send(data,lang='ru'):
                    req=urllib.request.Request('http://127.0.0.1:8765/stt',data=data,headers={'X-Lang':lang,'Content-Type':'application/octet-stream'})
                    try:
                        with urllib.request.urlopen(req) as r:return r.status,json.load(r)
                    except urllib.error.HTTPError as e:return e.code,json.load(e)
                self.assertEqual(send(b'\0\0'),(503,{'error':'stt_unavailable'}))
                self.assertEqual(send(b'\0'*480002)[0],413)
                self.assertEqual(send(b'\0')[0],400)
                self.assertEqual(send(b'\0\0','de')[0],400)
                self.assertEqual(send(b'RIFF0000')[0],400)
            finally:proc.terminate();proc.wait(timeout=5)
