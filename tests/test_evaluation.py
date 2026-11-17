"""Test oracle independence and reproducibility, not desired system scores."""
import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.run import METHODS, evaluate, load_cases, prepare_options, run, score


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = {case['id']: case for case in load_cases()}

    def test_fixture_labels_and_intervals(self):
        self.assertGreaterEqual(len(self.cases),12)
        self.assertEqual({c['category'] for c in self.cases.values()},
                         {'ordinary','challenging','changed','failure'})
        for case in self.cases.values():
            with self.subTest(case=case['id']):
                lengths = {a['id']:a['duration'] for a in case['assets']}
                requirements = case['expected']['requirements']
                self.assertEqual(len(requirements),len({r['label'] for r in requirements}))
                for requirement in requirements:
                    if case['expected']['feasible']:
                        self.assertTrue(requirement['acceptable_spans'])
                    for span in requirement['acceptable_spans']:
                        self.assertLess(span['start'],span['end'])
                        self.assertLessEqual(span['end'],lengths[span['asset_id']])

    def test_forged_evidence_metadata_cannot_cover_missing_span(self):
        case=self.cases['ordinary_single']
        result=dict(timeline=[dict(asset_id='a',start=1,end=5,evidence_ids=['solution'],
                                  required=True,score=100,reason='solution')],
                    options={'aspect':'16:9'},simulated_observed_duration=4,
                    production_topic_self_report=[{'verified':True}],issues=[],error=None)
        with patch('evaluation.run.review_timeline_evidence',side_effect=AssertionError('circular oracle')):
            metrics=score(case,result)
        self.assertEqual(metrics['coverage'],0)
        self.assertTrue(metrics['false_complete'])
        result['timeline'][0].update(start=16,end=20,evidence_ids=[],required=False,score=0)
        self.assertEqual(score(case,result)['coverage'],1)
        result['timeline'][0]['start']=17
        self.assertEqual(score(case,result)['coverage'],0)

    def test_oracle_rejects_invalid_and_overlapping_timelines(self):
        case=self.cases['ordinary_single']
        result,_,_=evaluate(case,'planner')
        for clips in ([dict(asset_id='missing',start=16,end=20)],
                      [dict(asset_id='a',start=16,end=41)],
                      [dict(asset_id='a',start=16,end=20)]*2):
            result['timeline']=clips
            self.assertFalse(score(case,result)['valid_timeline'])
            self.assertFalse(score(case,result)['all_requirements_met'])

    def test_semantics_and_internal_order_have_independent_failures(self):
        for name in ('challenging_synonym','challenging_negation','challenging_partial'):
            with self.subTest(case=name):
                _,metrics,_=evaluate(self.cases[name],'planner')
                self.assertEqual(metrics['coverage'],0)
        result,metrics,_=evaluate(self.cases['challenging_negation'],'planner')
        self.assertTrue(result['production_topic_self_report'][0]['verified'])
        self.assertTrue(metrics['false_complete'])
        _,metrics,_=evaluate(self.cases['challenging_merged_order'],'planner')
        self.assertEqual(metrics['coverage'],1)
        self.assertFalse(metrics['order_ok'])

    def test_followup_retains_and_replaces_options(self):
        ordered=prepare_options(self.cases['changed_order'])
        self.assertEqual(ordered['topics'],['problem','solution'])
        self.assertEqual(ordered['first_topic'],'solution')
        replaced=prepare_options(self.cases['changed_topics'])
        self.assertEqual(replaced['topics'],['result'])
        self.assertEqual(prepare_options(self.cases['changed_aspect'])['aspect'],'9:16')

    def test_repair_trace_records_fix_and_preserves_order(self):
        case=self.cases['challenging_repair_remove']
        _,before,_=evaluate(case,'planner')
        result,after,_=evaluate(case,'planner_repair')
        self.assertFalse(before['duration_ok'])
        self.assertTrue(after['all_requirements_met'])
        self.assertTrue(result['steps'][0]['repair_applied'])
        result,metrics,_=evaluate(self.cases['challenging_repair_order'],'planner_repair')
        self.assertTrue(metrics['duration_ok'])
        self.assertTrue(metrics['order_ok'])
        self.assertLessEqual(len(result['steps']),3)

    def test_expected_failures_are_not_successful_content(self):
        for case in self.cases.values():
            if case['expected']['feasible']:
                continue
            for method in METHODS:
                with self.subTest(case=case['id'],method=method):
                    _,metrics,_=evaluate(case,method)
                    self.assertFalse(metrics['all_requirements_met'])
                    self.assertTrue(metrics['expected_failure_flagged'])

    def test_runner_captures_exceptions_as_errors(self):
        case=copy.deepcopy(self.cases['ordinary_single'])
        case['instruction']='Create a 20-10 seconds recap.'
        result,metrics,_=evaluate(case,'planner')
        self.assertIn('ValueError',result['error'])
        self.assertFalse(metrics['all_requirements_met'])

    def test_export_and_determinism(self):
        original=load_cases()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory)
            report=run(root,2)
            self.assertEqual(len(report['rows']),len(original)*len(METHODS))
            self.assertEqual(len(list((root/'traces').glob('*.json'))),len(report['rows']))
            self.assertEqual(json.loads((root/'results.json').read_text()),report)
            self.assertTrue((root/'results.csv').read_text().startswith('case_id,category,method,'))
            self.assertTrue(all(row['error'] is None for row in report['rows']))
            self.assertEqual(load_cases(),original)


if __name__ == '__main__':
    unittest.main()
