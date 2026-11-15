import json
import unittest
from stt import Speech, STTUnavailable, MAX_BYTES
from unittest.mock import patch
import core

class FakeRecognizer:
    def __init__(self,model,rate): self.n=0;assert rate==16000
    def AcceptWaveform(self,data):self.n+=1;return self.n==1
    def Result(self):return json.dumps({'text':'первая часть'})
    def FinalResult(self):return json.dumps({'text':'вторая часть'})

class Tests(unittest.TestCase):
    def test_missing_model_is_not_empty_success(self):
        with self.assertRaises(STTUnavailable):Speech().transcribe(b'\0\0','ru')
    def test_invalid_language(self):
        with self.assertRaises(ValueError):Speech().transcribe(b'\0\0','xx')
    def test_odd_empty_oversized_rejected(self):
        for audio in (b'',b'\0',b'\0'*(MAX_BYTES+2)):
            with self.assertRaises(ValueError):Speech().transcribe(audio,'ru')
    def test_wav_container_rejected(self):
        with self.assertRaises(ValueError):Speech().transcribe(b'RIFF0000','ru')
    def test_final_and_intermediate_segments_combined(self):
        s=Speech();s.models['ru']=object();s.recognizer=FakeRecognizer
        r=s.transcribe(b'\0'*16000,'ru')
        self.assertEqual(r['text'],'первая часть вторая часть');self.assertEqual(r['lang'],'ru');self.assertGreaterEqual(r['ms'],0)
    def test_health_only_loaded_languages(self):
        s=Speech();s.models['en']=object();self.assertEqual(s.health(),{'ru':False,'en':True})
    @patch('core._request',return_value={'message':{'content':'{"ok":true}'}})
    def test_real_probe_payload_and_state(self,mock):
        self.assertTrue(core.warmup()['ready'])
        self.assertEqual(mock.call_args.args[0]['keep_alive'],-1)
    @patch('core._request',side_effect=OSError('offline'))
    def test_failed_probe_reports_unready(self,_):self.assertFalse(core.warmup()['ready'])
    @patch('core._request',return_value={'message':{'content':'{"facts":[{"field":"bleeding","value":"no","evidence":"Кровотечения нет"},{"field":"choking","value":"yes","evidence":"Подавился"}]}'}})
    def test_new_fields_and_keepalive(self,mock):
        facts=core.extract('Кровотечения нет. Подавился.')
        self.assertEqual([f['field'] for f in facts],['bleeding','choking'])
        payload=mock.call_args.args[0]
        self.assertEqual(payload['keep_alive'],-1)
        self.assertEqual(len(core.EXAMPLES),6)
        self.assertEqual(payload['format']['properties']['facts']['items']['properties']['value']['enum'],['yes','no'])
