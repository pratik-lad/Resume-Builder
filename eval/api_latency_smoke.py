"""Real-PDF API timing diagnostic, deliberately separate from labelled accuracy.

Runs serial fresh uploads and respects the existing low-fit/UCR gates.
Does not create gold or claim to exercise n8n. Never writes source inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

import httpx


def timings(values):
    if not values:
        return {'n': 0, 'p50': None, 'p95': None}
    ordered = sorted(values)
    pos = (len(ordered) - 1) * .95
    lo = int(pos)
    return {'n': len(values), 'p50': statistics.median(values),
            'p95': ordered[lo] + (ordered[min(lo+1, len(ordered)-1)]-ordered[lo]) * (pos-lo)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', type=Path, required=True)
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--jd-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=3)
    args = parser.parse_args()
    # Source identity is retained, not copied into an accuracy/gold dataset.
    source_hash = hashlib.sha256(args.resume.read_bytes()).hexdigest()
    job = next(j for j in json.loads(args.jobs.read_text(encoding='utf-8')) if j['id'] == args.jd_id)
    report = {'scope': 'Fresh real-PDF API uploads, same resume/JD repeated. Timing only; no gold truth, no n8n execution.',
              'resume': str(args.resume), 'resume_sha256': source_hash,
              'jd_id': args.jd_id, 'jd_title': job['title'], 'runs': []}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint():
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')

    with httpx.Client(base_url='http://localhost:8000', timeout=600) as client:
        report['health'] = client.get('/health').raise_for_status().json()
        for iteration in range(1, args.runs+1):
            record = {'iteration': iteration, 'stages': {}, 'outcome': 'running'}
            report['runs'].append(record)
            start = time.perf_counter()

            def post(stage, path, **kwargs):
                tick = time.perf_counter()
                response = client.post(path, **kwargs)
                record['stages'][stage] = {'seconds': time.perf_counter()-tick, 'http_status': response.status_code}
                print(f'API run {iteration}/{args.runs} {stage}: {record["stages"][stage]}', flush=True)
                checkpoint()
                response.raise_for_status()
                return response.json()

            try:
                with args.resume.open('rb') as stream:
                    ingest = post('ingest', '/v1/ingest', files={'file': (args.resume.name, stream, 'application/pdf')})
                record.update(run_id=ingest['run_id'], fact_count=ingest['fact_count'], sections=ingest['sections'])
                ref = {'run_id': ingest['run_id']}
                post('jd_extraction', '/v1/jd/extract', json={**ref, 'jd_text': job['title']+'\n\n'+job['description']})
                matched = post('match', '/v1/match', json=ref)
                record['score'] = matched['score_before']['jd_alignment_score']
                # Matches the checked-in n8n workflow's threshold, unchanged.
                if record['score'] < 25:
                    record['outcome'] = 'low_fit_rejected'
                else:
                    rewritten = post('rewrite', '/v1/optimize', json=ref)
                    record['ucr'] = rewritten['ucr']
                    record['rewrite_counts'] = {k: rewritten.get(k) for k in ('accepted', 'unchanged', 'reverted')}
                    record['rewrites'] = rewritten.get('rewrites', [])
                    rendered = post('render', '/v1/render', json=ref)
                    record['outcome'] = 'rendered'
                    record['download_url'] = rendered['download_url']
            except Exception as exc:
                record['outcome'] = 'blocked_ucr' if record.get('ucr', 0) > 0 else 'error'
                record['error'] = str(exc)
            record['total_seconds'] = time.perf_counter()-start
            checkpoint()
            print(f'API run {iteration} {record["outcome"]}: {record["total_seconds"]:.2f}s', flush=True)
    report['successful_upload_to_render_seconds'] = timings([r['total_seconds'] for r in report['runs'] if r['outcome']=='rendered'])
    report['all_attempts_seconds'] = timings([r['total_seconds'] for r in report['runs']])
    report['rewrite_seconds'] = timings([r['stages']['rewrite']['seconds'] for r in report['runs'] if 'rewrite' in r['stages']])
    report['resume_unchanged'] = hashlib.sha256(args.resume.read_bytes()).hexdigest() == source_hash
    checkpoint()
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs','health')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
