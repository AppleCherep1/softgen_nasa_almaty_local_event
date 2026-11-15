"""Interactive local microphone -> /stt test. No microphone/audio uploaded externally."""
import argparse
from array import array
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

PHRASES={
'ru':[
'Он не отвечает, но дышит нормально.',
'Он не дышит, только отдельные судорожные вдохи.',
'Боли в груди нет.',
'Дефибриллятор разряжен.',
'Кровотечения нет. Медик уже рядом.',
'Он подавился куском пищи.'
],
'en':[
'He is unresponsive but breathing normally.',
'He is not breathing, only gasping.',
'There is no chest pain.',
'The defibrillator battery is dead.',
'There is no bleeding. The medic is here.',
'He is choking on food.'
]}

def resample_pcm(pcm,source_rate,target_rate=16000):
    """Linear interpolation for a short diagnostic clip; no added dependencies."""
    if source_rate==target_rate:return pcm
    values=array('h');values.frombytes(pcm)
    if sys.byteorder!='little':values.byteswap()
    if not values:return b''
    count=int(len(values)*target_rate/source_rate);out=array('h')
    for i in range(count):
        x=i*source_rate/target_rate;j=min(int(x),len(values)-1);frac=x-j
        y=round(values[j]*(1-frac)+values[min(j+1,len(values)-1)]*frac)
        out.append(max(-32768,min(32767,y)))
    if sys.byteorder!='little':out.byteswap()
    return out.tobytes()

def tokens(text):return re.findall(r'\w+',text.casefold().replace('ё','е'))
def word_error_rate(expected,actual):
    a,b=tokens(expected),tokens(actual);prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(prev[j]+1,row[-1]+1,prev[j-1]+(x!=y)))
        prev=row
    return round(prev[-1]/max(1,len(a)),3)

def main():
    p=argparse.ArgumentParser();p.add_argument('--lang',choices=['ru','en','both'],default='both');p.add_argument('--seconds',type=int,default=7);p.add_argument('--device',type=int);p.add_argument('--output',default='vosk_microphone_results.json');a=p.parse_args()
    if not 1<=a.seconds<=15:p.error('seconds must be 1..15')
    try:import sounddevice as sd
    except (ImportError,OSError):print('Install microphone support: python -m pip install sounddevice');return 2
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=5) as r:health=json.load(r)
    except Exception:print('Start python server.py first.');return 2
    langs=['ru','en'] if a.lang=='both' else [a.lang]
    if any(not health.get('stt',{}).get(lang,False) for lang in langs):
        print('Vosk not ready:',json.dumps(health.get('stt_status',health.get('stt')),ensure_ascii=False));return 2
    try:
        rate=16000
        try:sd.check_input_settings(device=a.device,channels=1,dtype='int16',samplerate=rate)
        except Exception:rate=round(sd.query_devices(a.device,'input')['default_samplerate']);sd.check_input_settings(device=a.device,channels=1,dtype='int16',samplerate=rate)
    except Exception as exc:print('Microphone unavailable:',exc,'\nList devices: python -m sounddevice');return 2
    report={'at':datetime.now(timezone.utc).isoformat(),'health':health,'input_rate':rate,'output_rate':16000,'seconds':a.seconds,'rows':[],'note':'WER is lexical, not medical/semantic accuracy. Audio is not saved. human_meaning_review is manual.'}
    def save():Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    try:
        for lang in langs:
            for index,phrase in enumerate(PHRASES[lang],1):
                print(f'\n[{lang} {index}/6] Say: {phrase}')
                input(f'Press Enter, then speak during {a.seconds} seconds: ')
                row={'lang':lang,'expected':phrase,'recognized':None,'ms':None,'human_meaning_review':'not_reviewed'}
                try:
                    with sd.RawInputStream(samplerate=rate,channels=1,dtype='int16',device=a.device) as stream:
                        print('RECORDING...',flush=True);audio,overflowed=stream.read(a.seconds*rate)
                        pcm=bytes(audio)
                    if sys.byteorder!='little':
                        values=array('h');values.frombytes(pcm);values.byteswap();pcm=values.tobytes()
                    pcm=resample_pcm(pcm,rate)
                    request=urllib.request.Request('http://127.0.0.1:8765/stt',data=pcm,headers={'X-Lang':lang,'Content-Type':'application/octet-stream'})
                    with urllib.request.urlopen(request,timeout=120) as response:result=json.load(response)
                    row.update(recognized=result['text'],ms=result['ms'],input_overflow=bool(overflowed),wer=word_error_rate(phrase,result['text']))
                    print('Vosk:',result['text'] or '[empty]',f"({result['ms']} ms)")
                    report['rows'].append(row);save()
                    review=input('Did you say the full phrase and was its meaning preserved? y/n/? : ').strip().lower()
                    row['human_meaning_review']={'y':'preserved','n':'not_preserved'}.get(review,'uncertain')
                except urllib.error.HTTPError as exc:
                    row['error']=str(exc.code)+': '+exc.read().decode();report['rows'].append(row);print(row['error'])
                except Exception as exc:
                    row['error']=str(exc)
                    if not any(r is row for r in report['rows']):report['rows'].append(row)
                    print('Error:',exc)
                save()
    except (KeyboardInterrupt,EOFError):print('\nStopped; partial results saved.')
    save();print('Saved:',str(Path(a.output).resolve()));return 0
if __name__=='__main__':raise SystemExit(main())
