import unittest
from guards import apply_guards
from unittest.mock import patch
from core import Engine, GuardedFacts
from pathlib import Path
import tempfile

class GuardsTests(unittest.TestCase):
    def check(self,field,value,quote,text,expected):
        facts,warnings=apply_guards([{'field':field,'value':value,'evidence':quote}],text)
        actual=facts[0]['value'] if facts else 'unknown'
        self.assertEqual(actual,expected,(text,facts,warnings))
    def test_plain_breathing_does_not_establish_normal(self):
        for text in ['Он дышит','He is breathing','Она дышит, но не отвечает']:
            self.check('normal_breathing','yes',text,text,'unknown')
    def test_original_context_not_just_selected_quote(self):
        self.check('normal_breathing','yes','дышит нормально','Он не дышит нормально.','unknown')
        self.check('responsive','yes','отвечает','Он не отвечает.','unknown')
    def test_positive_normal_predicates(self):
        for text in ['Дышит нормально','Нормальное дыхание','breathing normally','normal breathing','Дыхание ровное и нормальное']:
            self.check('normal_breathing','yes',text,text,'yes')
    def test_no_breathing_predicates(self):
        for text in ['Не дышит','Дыхание отсутствует','Only gasping','He is not breathing','Отдельные судорожные вдохи']:
            self.check('normal_breathing','no',text,text,'no')
    def test_unsure_is_not_no(self):
        for field in ['responsive','normal_breathing','chest_pain','bleeding']:
            for text in ['сейчас не знаю','качество дыхания не оценивали','not assessed','I do not know']:
                self.check(field,'no',text,text,'unknown')
    def test_sleep_is_not_a_response_check(self):
        for text in ['Он просто спит','He is asleep']:
            self.check('responsive','no',text,text,'unknown')
    def test_unresponsive_remains_no(self):
        for text in ['Не отвечает','Не реагирует','does not respond to touch','He is unresponsive']:
            self.check('responsive','no',text,text,'no')
    def test_negated_unresponsive_is_not_no(self):
        self.check('responsive','no','unresponsive','He is not unresponsive','unknown')
    def test_equipment_presence_not_readiness(self):
        for value in ['yes','no']:
            self.check('aed_ready',value,'AED в другом модуле','AED в другом модуле','unknown')
        self.check('aed_ready','no','Дефибриллятор разряжен','Дефибриллятор разряжен','no')
        self.check('aed_ready','yes','AED рядом и готов','AED рядом и готов','yes')
    def test_conflict_does_not_reassure(self):
        self.check('normal_breathing','yes','Дышит нормально','Не дышит. Дышит нормально.','unknown')
    def test_unknown_is_not_invented_no(self):
        facts,warnings=apply_guards([], 'He is only gasping')
        self.assertEqual(facts,[]);self.assertEqual(warnings[0]['reason'],'missing_critical')
    def test_guard_audit_returned_and_saved(self):
        with tempfile.TemporaryDirectory() as d:
            e=Engine(str(Path(d)/'journal.sqlite3'));sid=e.start()['session_id']
            result=GuardedFacts([{'field':'normal_breathing','value':'yes','evidence':'дышит'}],'Он дышит')
            with patch('core.extract',return_value=result):p=e.propose(sid,'Он дышит')
            self.assertEqual(p['facts'],[]);self.assertEqual(p['guard_warnings'][0]['reason'],'breath')
            self.assertEqual(e.history(sid)[-1]['data']['raw_facts'][0]['value'],'yes')
