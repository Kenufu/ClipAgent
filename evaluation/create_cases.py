"""Rebuild the developer-authored fixture data (no planner imports or generated labels)."""
import json
from pathlib import Path


def cue(id, start, end, text, asset='a'):
    return dict(id=id, asset_id=asset, start=start, end=end, text=text, words=[])


def req(label, start=None, end=None, asset='a'):
    return {'label': label, 'acceptable_spans': [] if start is None else [dict(asset_id=asset, start=start, end=end)]}


BASE = [cue('intro', 1, 5, 'Welcome to our session.'),
        cue('problem', 8, 12, 'The problem is slow search.'),
        cue('solution', 16, 20, 'The solution is an indexed catalogue.'),
        cue('result', 24, 28, 'The result is faster retrieval.')]
CASES = []


def case(id, category, description, instruction, requirements, duration, *, transcript=None,
         first=None, feasible=True, prior=None, updates=None, offset=0, aspect='16:9', assets=None):
    CASES.append(dict(id=id, category=category, description=description,
        provenance='Developer-authored by the coding agent; curated synthetic transcript and labels; no independent human check; not sampled user data.',
        assets=assets or [dict(id='a', duration=40)], transcript=BASE if transcript is None else transcript,
        instruction=instruction, options={}, prior_request=prior, revision_options=updates or {},
        simulated_duration_offset_seconds=offset,
        expected=dict(requirements=requirements, duration_seconds=duration, first_requirement=first,
                      aspect=aspect, feasible=feasible)))

case('ordinary_single', 'ordinary', 'Direct late topic, early distractor.', 'Create a 4-6 seconds recap covering solution.', [req('solution',16,20)], [4,6])
case('ordinary_multiple', 'ordinary', 'Two separate required statements.', 'Create an 8-10 seconds recap covering problem and solution.', [req('problem',8,12), req('solution',16,20)], [8,10])
case('ordinary_chronological', 'ordinary', 'Chronological baseline can satisfy this brief.', 'Create a 4-6 seconds recap covering welcome.', [req('welcome',1,5)], [4,6])
case('ordinary_sources', 'ordinary', 'Evidence is in the second source.', 'Create a 4-6 seconds recap covering result.', [req('result',2,6,'b')], [4,6], transcript=[BASE[0],cue('b-result',2,6,'The result is faster retrieval.','b')], assets=[dict(id='a',duration=10),dict(id='b',duration=10)])
case('challenging_synonym', 'challenging', 'Semantic requirement expressed without the query keyword.', 'Create a 4-6 seconds recap covering cost.', [req('cost',16,20)], [4,6], transcript=[BASE[0],cue('price',16,20,'The price is ten dollars.')])
case('challenging_negation', 'challenging', 'Keyword hit explicitly does not give the requested answer.', 'Create a 4-6 seconds recap covering solution.', [req('solution',16,20)], [4,6], transcript=[cue('decoy',1,5,'No solution is presented here.'),cue('answer',16,20,'The solution is an indexed catalogue.')])
case('challenging_partial', 'challenging', 'Partial phrase is insufficient evidence for a specific claim.', 'Create a 4-6 seconds recap covering battery life.', [req('battery life',16,20)], [4,6], transcript=[cue('decoy',1,5,'Battery chemistry is discussed.'),cue('answer',16,20,'It lasts twelve hours per charge.')])
case('challenging_merged_order', 'challenging', 'Merged adjacent cues put the requested first statement after another one.', 'Create an 8-10 seconds recap covering problem and solution; put solution first.', [req('problem',1,5),req('solution',5,9)], [8,10], transcript=[cue('p',1,5,'The problem is slow search.'),cue('s',5,9,'The solution is indexing.')], first='solution')
prior=dict(instruction='Create an 8-10 seconds recap covering problem and solution.',options={})
case('changed_order', 'changed', 'Follow-up reuses transcript and prior parsed topics.', 'Put solution first.', [req('problem',8,12),req('solution',16,20)], [8,10], first='solution',prior=prior)
case('changed_topics', 'changed', 'Follow-up clears prior topics like the revise route.', 'Create a 4-6 seconds recap covering result.', [req('result',24,28)], [4,6],prior=prior,updates={'topics':[]})
case('changed_duration', 'changed', 'Follow-up changes duration while retaining the topic.', 'Make it 8-10 seconds.', [req('solution',16,20)], [8,10],prior=dict(instruction='Create a 4-6 seconds recap covering solution.',options={}))
case('changed_aspect', 'changed', 'Follow-up retains content and changes parsed aspect.', 'Export vertically.', [req('solution',16,20)], [4,6],aspect='9:16',prior=dict(instruction='Create a 4-6 seconds recap covering solution.',options={}))
case('failure_missing', 'failure', 'Requested topic does not occur; empty alternatives are deliberate.', 'Create a 4-6 seconds recap covering warranty.', [req('warranty')], [4,6],feasible=False)
case('failure_maximum', 'failure', 'Required speech cannot fit maximum duration.', 'Create a 1-3 seconds recap covering solution.', [req('solution',16,20)], [1,3],feasible=False)
case('failure_minimum', 'failure', 'Insufficient total source material.', 'Create a 20-25 seconds recap covering solution.', [req('solution',1,5)], [20,25],transcript=[cue('s',1,5,'The solution is indexing.')],assets=[dict(id='a',duration=6)],feasible=False)
case('failure_no_speech', 'failure', 'Preview fallback cannot establish spoken evidence.', 'Create a 4-6 seconds recap covering solution.', [req('solution')], [4,6],transcript=[],feasible=False)
case('challenging_repair_remove', 'challenging', 'Injected +3 second observation tests optional-context removal.', 'Create an 8-10 seconds recap covering solution.', [req('solution',16,20)], [8,10],offset=3)
case('challenging_repair_order', 'challenging', 'Injected -3 second observation exercises addition and possible order regression.', 'Create an 8-14 seconds recap covering problem and solution; put solution first.', [req('problem',8,12),req('solution',16,20)], [8,14],first='solution',offset=-3)

if __name__ == '__main__':
    Path(__file__).with_name('cases.json').write_text(json.dumps(CASES, indent=2) + '\n')
