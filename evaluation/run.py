"""Run with: python -m evaluation.run --repeats 20 --output evaluation/results."""
import argparse
import copy
import csv
import hashlib
import json
import math
import platform
import statistics
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from clipagent.planning import (build_timeline, parse_request, repair_duration,
                                review_timeline_evidence, validate_timeline)

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('chronological', 'planner', 'planner_repair')


def load_cases():
    return json.loads(Path(__file__).with_name('cases.json').read_text())


def chronological(assets, transcript, options):
    """Select whole chronological cues until minimum; skip cues exceeding maximum.

    Same padding as planner; coalesce overlap before duration accounting. No topic
    or ordering awareness. Empty speech yields source previews like the planner.
    """
    order = {asset['id']: i for i, asset in enumerate(assets)}
    lengths = {asset['id']: asset['duration'] for asset in assets}
    clips = []
    for cue in sorted(transcript, key=lambda c: (order[c['asset_id']], c['start'])):
        if sum(c['end'] - c['start'] for c in clips) >= options['min_seconds']:
            break
        clip = dict(asset_id=cue['asset_id'], start=round(max(0, cue['start']-.18),3),
                    end=round(min(lengths[cue['asset_id']],cue['end']+.22),3),
                    evidence_ids=[cue['id']], required=False)
        candidate = copy.deepcopy(clips)
        if candidate and candidate[-1]['asset_id'] == clip['asset_id'] and clip['start'] <= candidate[-1]['end'] + .12:
            candidate[-1]['end'] = max(candidate[-1]['end'], clip['end'])
            candidate[-1]['evidence_ids'].extend(clip['evidence_ids'])
        else:
            candidate.append(clip)
        if sum(c['end']-c['start'] for c in candidate) <= options['max_seconds']+.5:
            clips = candidate
    if not clips:
        clips = [dict(asset_id=a['id'],start=0,end=min(5,a['duration']), evidence_ids=[],required=False) for a in assets]
    return clips, []


def prepare_options(case):
    prior = case.get('prior_request')
    options = parse_request(prior['instruction'], prior['options']) if prior else case['options']
    options = dict(options)
    options.update(case.get('revision_options', {}))
    return parse_request(case['instruction'], options)


def execute(case, method):
    """Component adapter. Duration observations are simulated, never rendered."""
    options = prepare_options(case)
    assets, transcript = case['assets'], case['transcript']
    timeline, issues = (chronological if method == 'chronological' else build_timeline)(assets,transcript,options)
    steps = []
    for attempt in range(3 if method == 'planner_repair' else 1):
        predicted = validate_timeline(timeline, assets)
        observed = max(0, predicted + case['simulated_duration_offset_seconds'])
        step = dict(attempt=attempt, timeline=copy.deepcopy(timeline), predicted_duration=predicted,
                    simulated_observed_duration=observed)
        steps.append(step)
        if method != 'planner_repair' or attempt == 2:
            break
        revised, reason = repair_duration(timeline, transcript, assets, options, observed)
        step['repair_reason'] = reason
        step['repair_applied'] = revised is not None
        if revised is None:
            break
        validate_timeline(revised, assets)
        timeline = revised
    # Production self-report is diagnostic ONLY, never the scoring oracle.
    _, self_report, missing = review_timeline_evidence(timeline,transcript,options['topics'])
    issues = [i for i in issues if not i.startswith('No reliable spoken evidence found for:')]
    issues.extend(i for i in missing if i not in issues)
    if options['min_seconds']-.7 <= observed <= options['max_seconds']+.7:
        issues = [i for i in issues if 'duration' not in i.lower()]
    elif not any('duration' in i.lower() for i in issues):
        issues.append('Rendered duration is outside the requested range')
    return dict(options=options, timeline=timeline, steps=steps, issues=issues,
                production_topic_self_report=self_report,
                simulated_observed_duration=observed, error=None)


def score(case, result):
    """Independent oracle: explicit developer-authored intervals, no keyword scoring.

    A requirement is satisfied only when one full acceptable span is retained.
    Annotation IDs, reasons, scores and production coverage are ignored.
    """
    expected = case['expected']
    timeline = result.get('timeline', [])
    lengths = {a['id']: a['duration'] for a in case['assets']}
    valid = bool(timeline)
    intervals = defaultdict(list)
    for clip in timeline:
        start, end = clip['start'], clip['end']
        valid &= (clip['asset_id'] in lengths and math.isfinite(start) and math.isfinite(end)
                  and 0 <= start < end <= lengths.get(clip['asset_id'],0)+1e-6)
        intervals[clip['asset_id']].append((start,end))
    for spans in intervals.values():
        spans.sort()
        valid &= all(b[0] >= a[1]-1e-6 for a,b in zip(spans,spans[1:]))
    positions = {}
    for requirement in expected['requirements']:
        candidates = []
        offset = 0.0
        for index,clip in enumerate(timeline):
            for span in requirement['acceptable_spans']:
                if clip['asset_id'] == span['asset_id'] and clip['start'] <= span['start']+1e-6 and clip['end'] >= span['end']-1e-6:
                    candidates.append((offset + span['start']-clip['start'], index))
            offset += clip['end']-clip['start']
        positions[requirement['label']] = min(candidates) if candidates else None
    hits = sum(p is not None for p in positions.values())
    first = expected['first_requirement']
    order_ok = True
    if first:
        position = positions[first]
        order_ok = position is not None and position[1] == 0 and all(
            p is None or position[0] <= p[0]+1e-6 for p in positions.values())
    duration = result.get('simulated_observed_duration', 0)
    low, high = expected['duration_seconds']
    duration_ok = low-.7 <= duration <= high+.7
    aspect_ok = result.get('options',{}).get('aspect') == expected['aspect']
    passed = bool(valid and hits == len(positions) and order_ok and duration_ok and aspect_ok and not result.get('error'))
    return dict(requirements_met=hits, requirements_total=len(positions),
                coverage=hits/len(positions) if positions else 1.0,
                requirement_positions=positions, valid_timeline=bool(valid), duration_ok=duration_ok,
                order_ok=bool(order_ok), aspect_ok=aspect_ok, all_requirements_met=passed,
                feasible=expected['feasible'],
                expected_failure_flagged=(bool(result.get('issues')) and not result.get('error')) if not expected['feasible'] else None,
                false_complete=not passed and not result.get('issues') and not result.get('error'))


def evaluate(case, method):
    started = time.perf_counter_ns()
    try:
        result = execute(copy.deepcopy(case),method)
    except Exception as exc:
        result = dict(timeline=[], issues=[], error=f'{type(exc).__name__}: {exc}')
    elapsed = (time.perf_counter_ns()-started)/1e6
    return result, score(case,result), elapsed


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output, repeats):
    if repeats < 1:
        raise ValueError('repeats must be positive')
    output.mkdir(parents=True, exist_ok=True)
    traces = output/'traces'
    traces.mkdir(exist_ok=True)
    cases = load_cases()
    rows = []
    for case in cases:
        for method in METHODS:
            evaluate(case,method)  # one unrecorded warm-up per case and method
            runs = [evaluate(case,method) for _ in range(repeats)]
            result, metrics, _ = runs[0]
            if any(r != result or m != metrics for r,m,_ in runs):
                raise RuntimeError(f'Non-deterministic outputs: {case["id"]}/{method}')
            latencies = sorted(ms for _,_,ms in runs)
            row = dict(case_id=case['id'],category=case['category'],method=method,
                       **{k:v for k,v in metrics.items() if k != 'requirement_positions'},
                       duration_seconds=result.get('simulated_observed_duration'),
                       repair_count=sum(s.get('repair_applied',False) for s in result.get('steps',[])),
                       error=result['error'],latency_median_ms=statistics.median(latencies),
                       latency_p95_ms=latencies[math.ceil(.95*len(latencies))-1])
            rows.append(row)
            (traces/f'{case["id"]}__{method}.json').write_text(json.dumps(dict(case=case,result=result,metrics=metrics,latency_ms=latencies),indent=2)+'\n')
    summaries = {}
    for method in METHODS:
        selected = [r for r in rows if r['method'] == method]
        feasible = [r for r in selected if r['feasible']]
        failures = [r for r in selected if not r['feasible']]
        summaries[method] = dict(cases=len(selected),feasible_cases=len(feasible),
            feasible_passes=sum(r['all_requirements_met'] for r in feasible),
            requirement_coverage=sum(r['requirements_met'] for r in selected)/sum(r['requirements_total'] for r in selected),
            expected_failures=len(failures),failures_flagged=sum(r['expected_failure_flagged'] for r in failures),
            false_complete=sum(r['false_complete'] for r in selected),errors=sum(bool(r['error']) for r in selected),
            median_case_latency_ms=statistics.median(r['latency_median_ms'] for r in selected))
    try:
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except (OSError,subprocess.CalledProcessError):
        revision = None
    metadata = dict(generated_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
        platform=platform.platform(),git_head=revision,repeats=repeats,warmups_per_case_method=1,
        command=f'python -m evaluation.run --repeats {repeats} --output {output}',
        source_sha256={p:digest(ROOT/p) for p in ['clipagent/planning.py','clipagent/service.py','evaluation/cases.json','evaluation/run.py','evaluation/create_cases.py']},
        label_provenance='Developer-authored by the coding agent; no independent human check; no held-out sample.',
        scope='Synthetic component evaluation; duration observations simulated; no rendering, ASR, API or persistence.',
        latency_scope='Deep copy, request parsing, planning, optional repair and production evidence diagnostic; excludes independent scoring, fixture loading, file IO, ASR and rendering.')
    report = dict(metadata=metadata,summary=summaries,rows=rows)
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    with (output/'results.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summaries,indent=2))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'evaluation/results')
    parser.add_argument('--repeats',type=int,default=20)
    args=parser.parse_args()
    run(args.output,args.repeats)
