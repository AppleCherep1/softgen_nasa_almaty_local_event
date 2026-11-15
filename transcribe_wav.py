"""Send a local PCM16/mono/16kHz WAV as raw PCM to /stt."""
import argparse
import json
import urllib.request
import wave
from stt import MAX_BYTES

def main():
    p=argparse.ArgumentParser();p.add_argument('wav');p.add_argument('--lang',choices=['ru','en'],required=True);a=p.parse_args()
    with wave.open(a.wav,'rb') as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype())!=(1,2,16000,'NONE'):p.error('WAV must be uncompressed PCM16 mono 16000 Hz')
        if not 0<w.getnframes()<=240000:p.error('Duration must be >0 and <=15 seconds')
        data=w.readframes(w.getnframes())
    if len(data)>MAX_BYTES:p.error('Too much audio')
    req=urllib.request.Request('http://127.0.0.1:8765/stt',data=data,headers={'Content-Type':'application/octet-stream','X-Lang':a.lang})
    try:
        with urllib.request.urlopen(req,timeout=120) as response:print(json.dumps(json.load(response),ensure_ascii=False,indent=2))
    except urllib.error.HTTPError as e:
        print(e.code,e.read().decode());return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
