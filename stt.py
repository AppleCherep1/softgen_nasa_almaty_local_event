"""Offline raw little-endian PCM16/mono/16kHz speech transcription with Vosk."""
import json
import threading
from pathlib import Path
from time import perf_counter

SAMPLE_RATE=16000
MAX_BYTES=15*SAMPLE_RATE*2
MODEL_DIR=Path(__file__).with_name('models')
PATHS={'ru':('vosk-model-small-ru','vosk-model-small-ru-0.22'), 'en':('vosk-model-small-en-us-0.15',)}

class STTUnavailable(Exception): pass

class Speech:
    def __init__(self):
        self.models={}; self.recognizer=None; self.lock=threading.Lock()
        self.states={lang:('loading' if any((MODEL_DIR/name).is_dir() for name in names) else 'not_installed') for lang,names in PATHS.items()}
    def load(self):
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
        except (ImportError,OSError):
            with self.lock:
                self.states={lang:('dependency_missing' if status=='loading' else status) for lang,status in self.states.items()}
            return
        with self.lock: self.recognizer=KaldiRecognizer
        for lang, names in PATHS.items():
            folder=next((MODEL_DIR/name for name in names if (MODEL_DIR/name).is_dir()),None)
            if folder is None:
                with self.lock: self.states[lang]='not_installed'
                continue
            with self.lock: self.states[lang]='loading'
            try: model=Model(str(folder))
            except Exception:
                with self.lock: self.states[lang]='error'
                continue
            with self.lock:
                self.models[lang]=model
                self.states[lang]='ready'
    def health(self):
        with self.lock: return {lang:lang in self.models for lang in PATHS}
    def statuses(self):
        with self.lock: return dict(self.states)
    def transcribe(self,pcm,lang):
        if lang not in PATHS: raise ValueError('invalid_language')
        if not pcm or len(pcm)>MAX_BYTES or len(pcm)%2: raise ValueError('invalid_pcm')
        if pcm[:4] in (b'RIFF',b'OggS',b'\x1aE\xdf\xa3') or pcm[:3]==b'ID3':
            raise ValueError('raw_pcm_required')
        with self.lock: model=self.models.get(lang); recognizer=self.recognizer
        if model is None or recognizer is None: raise STTUnavailable()
        started=perf_counter(); segments=[]
        try:
            rec=recognizer(model,SAMPLE_RATE)
            for offset in range(0,len(pcm),8000):
                if rec.AcceptWaveform(pcm[offset:offset+8000]):
                    segments.append(json.loads(rec.Result()).get('text',''))
            segments.append(json.loads(rec.FinalResult()).get('text',''))
        except Exception as exc: raise STTUnavailable() from exc
        return {'text':' '.join(s for s in segments if s).strip(),'lang':lang,'ms':round((perf_counter()-started)*1000)}
