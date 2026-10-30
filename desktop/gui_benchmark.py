"""Cold/warm acceptance runs through the real GUI controller and frozen worker."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker-exe',required=True)
    parser.add_argument('--resume',required=True,help='Path to a local PDF or DOCX test resume')
    parser.add_argument('--output',required=True)
    parser.add_argument('--fixtures',default='full-stack,salesforce,java,databricks,aws,azure-genai,qa')
    parser.add_argument('--modes', default='cold,warm')
    parser.add_argument('--repetitions', type=int, default=1)
    args=parser.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ.update(RESUME_DESKTOP_EDITION='projects',RESUME_DESKTOP_DATA=str(out/'data'),QT_QPA_PLATFORM='offscreen')
    os.environ.pop('RESUME_DESKTOP_SELF_TEST_MS',None)
    # Exercise the frozen worker without Python or CUDA SDK directories on PATH.
    os.environ['PATH']=str(Path(os.environ['WINDIR'])/'System32')
    from desktop.bootstrap import initialize
    initialize()
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtCore import QTimer, QObject, Signal
    from desktop.app import Window
    import desktop.controller as controller
    from desktop.storage import atomic_json
    worker=os.path.abspath(args.worker_exe)
    controller.worker_command=lambda:[worker,'--worker']
    app=QApplication([]);window=Window();window.show()
    window.resume.setText(args.resume)
    pending=[(f,m,repeat) for repeat in range(1,args.repetitions+1)
             for f in args.fixtures.split(',') for m in args.modes.split(',')]
    results=[];active={};last_tick=time.perf_counter();max_gap=0.0;started=0.0
    QMessageBox.warning=lambda *a:print('GUI_MESSAGE',str(a[-1]),flush=True)
    heartbeat=QTimer();heartbeat.setInterval(20)
    def beat():
        nonlocal last_tick,max_gap
        now=time.perf_counter();max_gap=max(max_gap,now-last_tick);last_tick=now
    heartbeat.timeout.connect(beat);heartbeat.start()
    class InterferenceMonitor(QObject):
        detected=Signal(object)
    interference=InterferenceMonitor()
    stopping=threading.Event()
    def sample_gpu():
        while not stopping.wait(1):
            try:
                import psutil
                owned={p.pid for p in psutil.Process().children(recursive=True)}
                # A just-cancelled owned server can briefly disappear from the
                # process tree before Windows finishes exiting it. Its bundle
                # is still ours; distinguish external installed model servers.
                runtime_root=str(Path(worker).parent).casefold()+os.sep
                other=[p.info['pid'] for p in psutil.process_iter(['pid','name','exe'])
                       if p.info['name']=='llama-server.exe' and p.info['pid'] not in owned
                       and not str(p.info.get('exe') or '').casefold().startswith(runtime_root)]
                if other:
                    active['other_model_pids']=sorted(set(active.get('other_model_pids',[]))|set(other))
                    interference.detected.emit(other)
                r=subprocess.run(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                value=max(int(v.strip()) for v in r.stdout.splitlines())
                active['peak_device_gpu_used_mib']=max(active.get('peak_device_gpu_used_mib',0),value)
            except (OSError,ValueError,subprocess.SubprocessError):pass
    gpu_thread=threading.Thread(target=sample_gpu,daemon=True);gpu_thread.start()
    deadline=QTimer();deadline.setSingleShot(True)
    def persist():atomic_json(out/'results.json',results)
    def next_job():
        nonlocal active,started,max_gap,last_tick
        if not pending:
            window.close();app.quit();return
        fixture,mode,repeat=pending.pop(0)
        window.resume.setText(args.resume)
        if mode=='cold':window.controller.cancel()
        key=fixture+'-'+mode+(f'-run-{repeat}' if args.repetitions>1 else '')
        active={'key':key,'fixture':fixture,'mode':mode,'repeat':repeat,'scope':'source GUI and real frozen worker; Generate to preview and autosave'}
        window.jd.setPlainText((ROOT/'desktop/fixtures'/f'{fixture}-jd.txt').read_text(encoding='utf-8'))
        window.controller.peak_rss=0
        max_gap=0;last_tick=time.perf_counter();started=last_tick
        print('START',active['key'],flush=True)
        deadline.start(900000)
        window.generate_draft()
    def failed(message):
        deadline.stop()
        active.update(success=False,error=message,seconds=round(time.perf_counter()-started,3))
        results.append(dict(active));persist();window.controller.cancel()
        QTimer.singleShot(150,next_job)
    deadline.timeout.connect(lambda:failed('Fifteen-minute job deadline reached'))
    def stop_for_other_model(pids):
        if active and not active.get('interference_stopped'):
            active['interference_stopped']=True
            pending.clear()
            failed('Another application started its model; this benchmark stopped to avoid interference.')
    interference.detected.connect(stop_for_other_model)
    def event(item):
        if item['status']=='progress':
            print(active.get('key'),item.get('message'),flush=True)
        elif item['status']=='error':failed(item.get('message','Worker error'))
        elif item['status']=='complete' and item['kind']=='draft':
            deadline.stop()
            window.refresh_preview();window.autosave()
            doc=window.document
            active.update(success=True,seconds=round(time.perf_counter()-started,3),
                          calls=doc['model_calls'],model=doc['model'],
                          peak_gui_worker_tree_rss_bytes=window.controller.peak_rss,
                          max_event_loop_gap_seconds=round(max_gap,4),
                          summary_methods=doc['profile_metadata']['summary_methods'],
                          warnings=doc['quality']['warnings'],profile_warnings=doc['quality']['profile_warnings'],
                          coverage=doc['quality']['coverage'])
            active['timing_gate_pass']=active['seconds']<=300 and max_gap<30 and doc['model']['backend']=='llama.cpp-cuda' and not active.get('other_model_pids')
            atomic_json(out/(active['key']+'.json'),doc)
            results.append(dict(active));persist()
            print('RESULT',json.dumps(active),flush=True)
            QTimer.singleShot(150,next_job)
    window.controller.event.connect(event)
    QTimer.singleShot(0,next_job)
    try:app.exec()
    finally:
        stopping.set();gpu_thread.join(timeout=4)
        window.controller.close()


if __name__=='__main__':main()
