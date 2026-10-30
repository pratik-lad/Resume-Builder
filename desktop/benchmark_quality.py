"""Real offline model comparisons. Separate profiles; never touch saved user drafts."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',choices=['qwen3','qwen35','phi'],required=True)
    parser.add_argument('--resume',required=True,help='Path to a local PDF or DOCX test resume')
    parser.add_argument('--fixtures',default='full-stack,salesforce,java,databricks,aws,azure-genai,qa')
    parser.add_argument('--repeats',type=int,default=1)
    parser.add_argument('--warm',action='store_true')
    parser.add_argument('--label',default='comparison')
    args=parser.parse_args()
    out=ROOT/'build/quality-benchmark'/f'{args.label}-{args.candidate}'
    out.mkdir(parents=True,exist_ok=True)
    os.environ.update(RESUME_DESKTOP_DATA=str(out/'data'),RESUME_DESKTOP_EDITION='projects',QT_QPA_PLATFORM='offscreen',RESUME_TRACE_MODEL='1')
    from desktop.bootstrap import initialize
    initialize()
    import logging
    logging.basicConfig(filename=out/"validation.log",level=logging.INFO,encoding="utf-8")
    import desktop.runtime as runtime_module
    from desktop.project_generation import generate
    from desktop.reference_layout import html
    from desktop.storage import atomic_json
    from desktop.draft import export
    from PySide6.QtWidgets import QApplication,QTextBrowser
    import psutil
    app=QApplication([]);preview=QTextBrowser()
    spec=json.loads((ROOT/'desktop/assets.json').read_text())
    spec['model']=json.loads((ROOT/'desktop/model_candidates.json').read_text())[args.candidate]
    assets=out/'assets';(assets/'models').mkdir(parents=True,exist_ok=True)
    model=spec['model'];source=ROOT/'build/model-candidates'/model['filename']
    if not source.exists():source=ROOT/'build/desktop-assets/models'/model['filename']
    if not source.exists():
        from desktop.prepare_assets import download_verified
        source=ROOT/'build/model-candidates'/model['filename']
        download_verified('https://huggingface.co/'+model['repository']+'/resolve/'+model['revision']+'/'+model['filename'],source,model['sha256'],model['size'],print)
    target=assets/'models'/model['filename']
    if not target.exists():target.hardlink_to(source)
    files=[{'path':'models/'+model['filename'],'size':model['size'],'sha256':model['sha256']}]
    for folder in ['runtime','runtime-cuda']:
        for original in (ROOT/'build/desktop-assets'/folder).glob('*'):
            if not original.is_file():continue
            destination=assets/folder/original.name;destination.parent.mkdir(exist_ok=True)
            if not destination.exists():destination.hardlink_to(original)
            with original.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
            files.append({'path':folder+'/'+original.name,'size':original.stat().st_size,'sha256':digest})
    (assets/'manifest.json').write_text(json.dumps({'spec':spec,'files':files}))
    runtime_module.ASSETS=assets
    runtime=runtime_module.Runtime()
    process=psutil.Process()
    results=[]
    result_path=out/'results.json'
    if result_path.exists():results=json.loads(result_path.read_text())
    def gpu_used():
        try:
            r=subprocess.run(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return max(int(v.strip()) for v in r.stdout.splitlines())
        except Exception:return None
    try:
        for fixture in args.fixtures.split(','):
            for repeat in range(args.repeats):
                for mode in (['cold','warm'] if args.warm else ['cold']):
                    key=f'{fixture}-{repeat+1}-{mode}'
                    if any(r['key']==key for r in results):continue
                    if mode=='cold':runtime.stop()
                    item={'key':key,'candidate':args.candidate,'fixture':fixture,'mode':mode,'reference_8gb':False,
                          'gpu_device_used_before_mib':gpu_used(),'timing_scope':'source generator, preview and autosave; exports separate'}
                    peak=[0];gpu_peak=[0];gaps=[0.0];done=threading.Event()
                    def monitor():
                        tick=0;last=time.perf_counter()
                        while not done.wait(.25):
                            now=time.perf_counter();gaps[0]=max(gaps[0],now-last);last=now
                            try:
                                rss=sum(p.memory_info().rss for p in [process]+process.children(recursive=True) if p.is_running())
                                peak[0]=max(peak[0],rss)
                                if tick%8==0:gpu_peak[0]=max(gpu_peak[0],gpu_used() or 0)
                                tick+=1
                            except psutil.Error:pass
                    thread=threading.Thread(target=monitor,daemon=True);thread.start()
                    def progress(stage,message):print(key,stage,message,flush=True)
                    start=time.perf_counter()
                    try:
                        jd=(ROOT/'desktop/fixtures'/f'{fixture}-jd.txt').read_text(encoding='utf-8')
                        document=generate({'resume':args.resume,'jd':jd},runtime,progress)
                        preview.setHtml(html(document));app.processEvents()
                        atomic_json(out/(key+'.json'),document)
                        item.update(seconds=round(time.perf_counter()-start,3),calls=document['model_calls'],repairs=document['repair_calls'],
                                    quality_repairs=document['quality_repair_calls'],model=document['model'],
                                    summary_methods=document['profile_metadata']['summary_methods'],coverage=document['quality']['coverage'],
                                    warnings=document['quality']['warnings'],profile_warnings=document['quality']['profile_warnings'],
                                    ledger_counts={status:sum(r['status']==status and r['required'] for r in document['requirement_evidence']['rows']) for status in ['supported','partial','missing','review separately']})
                        export_start=time.perf_counter()
                        for kind in ['docx','html']:
                            artifact=export({'document':document,'kind':kind,'destination':str(out/(key+'.'+kind))},lambda *a:None)['artifact']
                            shutil.copyfile(artifact,out/(key+'.'+kind))
                        item['export_seconds']=round(time.perf_counter()-export_start,3)
                        item['success']=True
                    except Exception as error:
                        import traceback
                        item.update(success=False,error=str(error),seconds=round(time.perf_counter()-start,3),requests=runtime.request_metrics)
                        traceback.print_exc()
                    finally:
                        done.set();thread.join(timeout=4)
                        item.update(max_monitor_gap_seconds=round(gaps[0],3),timing_valid=gaps[0]<30,peak_process_tree_rss_bytes=peak[0],peak_gpu_device_used_mib=gpu_peak[0],gpu_memory_scope='entire device including other applications')
                        results.append(item);atomic_json(result_path,results)
                        print('RESULT',json.dumps(item),flush=True)
    finally:
        runtime.stop();preview.close()


if __name__=='__main__':main()
