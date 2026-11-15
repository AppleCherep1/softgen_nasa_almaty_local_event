import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import Engine, validate, BackendError, EXAMPLES

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.e=Engine(str(Path(self.tmp.name)/'test.sqlite')); self.sid=self.e.start()['session_id']
    def test_prompt_example_quotes_are_literal(self):
        import json
        for i in range(0,len(EXAMPLES),2):
            validate(json.loads(EXAMPLES[i+1]['content']),EXAMPLES[i]['content'])
    def test_gravity_must_be_explicit(self):
        from mission import validate_context, applicability
        c=validate_context({'phase':'transit_to_mars'})
        self.assertEqual(c['environment'],'unknown')
        self.assertEqual(applicability({},c)['reason'],'environment_required')
    def test_earth_protocol_not_applied_to_microgravity(self):
        from mission import validate_context, applicability
        r=applicability({'review_status':'reviewed','environments':['earth_surface']},validate_context({'environment':'microgravity'}))
        self.assertEqual(r['reason'],'environment_not_covered')
    @patch('core.extract',return_value=[])
    def test_clarification_saved_and_stale_reply_rejected(self,_):
        sid=self.e.start({'environment':'microgravity'})['session_id']
        p=self.e.propose(sid,'дышит')
        c=self.e.confirm(sid,p['proposal_id'],{'responsive':'no','normal_breathing':'unknown'})
        out=self.e.clarify(sid,c['confirmation_id'],'normal_breathing','yes')
        self.assertEqual(out['confirmed_facts']['normal_breathing'],'yes')
        self.assertEqual(out['questions'],[])
        self.assertIsNone(out['instruction'])
        with self.assertRaises(ValueError):self.e.clarify(sid,c['confirmation_id'],'normal_breathing','no')
    def test_scenario_blocks_non_microgravity(self):
        from scenario import build_preview
        from mission import validate_context
        r=build_preview(validate_context({'environment':'mars_surface'}),{'responsive':'no','normal_breathing':'no'}, {})
        self.assertEqual(r['steps'],[])
    def test_no_automatic_aed_when_unready(self):
        from scenario import build_preview
        from mission import validate_context
        r=build_preview(validate_context({'environment':'microgravity','link':'unavailable'}),{'responsive':'no','normal_breathing':'no','aed_ready':'no'}, {'aed':{'ready':'yes'}})
        self.assertEqual(r['aed_effective_status'],'no')
        self.assertNotIn('aed_ready',[x['id'] for x in r['steps']])
        self.assertFalse(r['clinical_protocol_enabled'])
    def test_unknown_surface_prevents_aed_ready_step(self):
        from scenario import build_preview
        from mission import validate_context
        r=build_preview(validate_context({'environment':'microgravity'}),{'responsive':'no','normal_breathing':'no'}, {'aed':{'ready':'yes'},'cmrs':{'ready':'yes'}})
        self.assertIn('aed_check',[x['id'] for x in r['steps']])
    @patch('core.extract',return_value=[])
    def test_scenario_ack_and_stale_plan(self,_):
        sid=self.e.start({'environment':'microgravity'})['session_id']
        p=self.e.propose(sid,'не отвечает')
        c=self.e.confirm(sid,p['proposal_id'],{'responsive':'no','normal_breathing':'yes'})
        plan=self.e.scenario(sid,c['confirmation_id'])
        self.assertTrue(self.e.mark_step(sid,plan['plan_id'],'call_crew')['saved'])
        with self.assertRaises(ValueError):self.e.mark_step(sid,plan['plan_id'],'call_crew')
        self.e.propose(sid,'состояние изменилось')
        with self.assertRaises(ValueError):self.e.mark_step(sid,plan['plan_id'],'monitor')
    def test_invented_quote_rejected(self):
        with self.assertRaises(ValueError): validate({'facts':[{'field':'responsive','value':'no','evidence':'без сознания'}]},'Он спит')
    def test_reported_qwen_response_unknown_placeholders(self):
        text='He is unresponsive but breathing. The AED battery is dead.'
        facts=[
            {'field':'responsive','value':'no','evidence':'He is unresponsive'},
            {'field':'normal_breathing','value':'unknown','evidence':'He is breathing'},
            {'field':'chest_pain','value':'unknown','evidence':'No mention'},
            {'field':'aed_ready','value':'no','evidence':'The AED battery is dead'},
            {'field':'medic_present','value':'unknown','evidence':'No mention'}]
        self.assertEqual(validate({'facts':facts},text),[facts[0],facts[3]])
    def test_no_without_literal_evidence_still_rejected(self):
        with self.assertRaises(ValueError):
            validate({'facts':[{'field':'normal_breathing','value':'no','evidence':'He is not breathing'}]},'He is breathing')
    def test_case_only_quote_restored_from_source(self):
        facts=validate({'facts':[{'field':'normal_breathing','value':'no','evidence':'отдельные судорожные вдохи'}]},'Он не отвечает. Отдельные судорожные вдохи.')
        self.assertEqual(facts[0]['evidence'],'Отдельные судорожные вдохи')
    def test_case_matching_does_not_allow_word_changes(self):
        with self.assertRaises(ValueError):
            validate({'facts':[{'field':'normal_breathing','value':'no','evidence':'НЕ дышит'}]},'Дышит нормально')
    def test_duplicates_rejected(self):
        f={'field':'responsive','value':'no','evidence':'не отвечает'}
        with self.assertRaises(ValueError): validate({'facts':[f,f]},'не отвечает')
    @patch('core.extract',side_effect=BackendError())
    def test_no_model_is_explicit_manual_mode(self,_):
        p=self.e.propose(self.sid,'дышит'); self.assertEqual(p['status'],'manual_required'); self.assertIsNone(p['instruction'])
    @patch('core.extract',return_value=[])
    def test_unknown_breathing_prompts_and_replay_rejected(self,_):
        p=self.e.propose(self.sid,'дышит'); r=self.e.confirm(self.sid,p['proposal_id'],{'responsive':'no','normal_breathing':'unknown'})
        self.assertEqual(r['questions'][0]['field'],'normal_breathing')
        with self.assertRaises(ValueError): self.e.confirm(self.sid,p['proposal_id'],{'responsive':'yes'})
    @patch('core.extract',return_value=[])
    def test_no_clinical_action_even_with_confirmed_facts(self,_):
        p=self.e.propose(self.sid,'не отвечает и не дышит'); r=self.e.confirm(self.sid,p['proposal_id'],{'responsive':'no','normal_breathing':'no'})
        self.assertFalse(r['clinical_protocol_enabled']); self.assertIsNone(r['instruction'])
    @patch('core.extract',return_value=[])
    def test_stale_confirmation(self,_):
        old=self.e.propose(self.sid,'не отвечает'); self.e.propose(self.sid,'пришел в себя')
        with self.assertRaises(ValueError): self.e.confirm(self.sid,old['proposal_id'],{'responsive':'no'})
    def test_cross_session_blocked(self):
        other=self.e.start()['session_id']
        with patch('core.extract',return_value=[]): p=self.e.propose(self.sid,'текст')
        with self.assertRaises(ValueError): self.e.confirm(other,p['proposal_id'],{'responsive':'yes'})

if __name__=='__main__': unittest.main()
