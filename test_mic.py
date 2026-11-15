from array import array
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import core
from mic_check import resample_pcm, word_error_rate, PHRASES
from stt import Speech

class Tests(unittest.TestCase):
    def test_no_models_status_is_not_loading(self):
        with tempfile.TemporaryDirectory() as d,patch('stt.MODEL_DIR',Path(d)):
            s=Speech();self.assertEqual(s.statuses(),{'ru':'not_installed','en':'not_installed'})
    def test_model_loading_and_corrupt_state(self):
        with tempfile.TemporaryDirectory() as d,patch('stt.MODEL_DIR',Path(d)):
            (Path(d)/'vosk-model-small-ru').mkdir();s=Speech()
            self.assertEqual(s.statuses()['ru'],'loading')
            def fail(*args):raise ValueError('corrupt')
            with patch.dict('sys.modules',{'vosk':SimpleNamespace(Model=fail,KaldiRecognizer=object,SetLogLevel=lambda x:None)}):s.load()
            self.assertEqual(s.statuses()['ru'],'error')
            self.assertFalse(s.health()['ru'])
    def test_missing_dependency_distinct(self):
        with tempfile.TemporaryDirectory() as d,patch('stt.MODEL_DIR',Path(d)):
            (Path(d)/'vosk-model-small-ru').mkdir();s=Speech()
            with patch.dict('sys.modules',{'vosk':None}):s.load()
            self.assertEqual(s.statuses()['ru'],'dependency_missing')
    @patch('core._request',side_effect=urllib.error.HTTPError('url',404,'missing',{},None))
    def test_llm_not_installed_distinct(self,_):self.assertEqual(core.warmup()['status'],'not_installed')
    @patch('core._request',side_effect=urllib.error.URLError('refused'))
    def test_ollama_unavailable_distinct(self,_):self.assertEqual(core.warmup()['status'],'unavailable')
    def test_resample_duration(self):
        pcm=array('h',[0]*48000).tobytes();self.assertEqual(len(resample_pcm(pcm,48000)),32000)
    def test_missing_negation_changes_metric(self):
        self.assertGreater(word_error_rate('He is not breathing','he is breathing'),0)
        self.assertEqual(word_error_rate('Боли нет.','боли нет'),0)
    def test_six_phrases_each(self):self.assertEqual([len(PHRASES[x]) for x in ('ru','en')],[6,6])
