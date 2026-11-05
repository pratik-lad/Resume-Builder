"""Isolated GUI acceptance: pending inputs must not relabel completed jobs."""
from __future__ import annotations
import copy
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'api')]


def main():
    if not os.environ.get('RESUME_DESKTOP_DATA'):
        raise RuntimeError('This check requires an isolated data directory.')
    from desktop.bootstrap import initialize, DATA
    initialize()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QTextCursor
    from docx import Document
    from desktop.app import Window
    from desktop.controller import JobController
    from desktop.project_generation import generate
    from desktop.test_project_quality import ProjectRuntime
    from desktop.storage import load_draft
    from desktop.draft import export
    from desktop.project_rules import report

    app=QApplication.instance() or QApplication([])
    source=DATA/'Candidate input with spaces.docx'
    doc=Document()
    for line in ('Alex Example','alex@example.test','20 years of experience',
                 'Professional Experience','Built Python services using Docker.',
                 'Education','BSc Computer Science | Example University | 2021'):
        doc.add_paragraph(line)
    doc.save(source)
    jd_a='Platform Engineer\n**Experience:** 8+ Years\nRequired Python and Docker.'
    jd_b='Platform Engineer\nExperience required: 12+ Years\nRequired Python and Docker.'
    jd_c='Platform Engineer\nExperience: 7 years\nRequired Azure and Terraform.'
    initial=generate({'resume':str(source),'jd':jd_a,'_job_id':'initial'},ProjectRuntime(),lambda *a:None)
    window=Window();window.resume.setText(str(source));window.jd.setPlainText(jd_a)
    window.set_document(copy.deepcopy(initial))
    window.jd.setPlainText(jd_b)
    assert window.document['jd']==jd_a and window.document['comparison_jd']==jd_b
    assert len(window.document['projects'])==5
    assert report(window.document)['project_count']['comparison_policy']['project_count']==6
    original_text=copy.deepcopy(window.document['sections'])
    for kind in ('docx','html'):
        path=DATA/('comparison.'+kind)
        out=export({'document':window.document,'kind':kind,'destination':str(path)},lambda *a:None)
        if kind=='html':
            html=Path(out['artifact']).read_text(encoding='utf-8')
            assert 'Comparison uses a different JD' in html and '6-project target' in html
    assert window.document['sections']==original_text

    # Use the real controller queue and event filtering, replacing process startup only.
    window.controller._start=lambda job:setattr(window.controller,'active',job)
    window.generate_draft()
    active=copy.deepcopy(window.controller.active)
    window.jd.setPlainText(jd_c);window.resume.setText(str(DATA/'next candidate.docx'))
    window.generate_draft()
    queued=copy.deepcopy(window.controller.waiting)
    window.jd.setPlainText(jd_a)
    assert window.controller.active['payload']['jd']==jd_b
    assert window.controller.waiting['payload']['jd']==jd_c
    old_id=window.draft_id
    project_row=next(i for i,s in enumerate(window.document['sections']) if s['key']=='projects')
    window.sections.setCurrentRow(project_row)
    window.editor.moveCursor(QTextCursor.MoveOperation.End)
    window.editor.insertPlainText('\nLate edit to the preceding resume.')
    result=generate({**active['payload'],'_job_id':active['job_id']},ProjectRuntime(),lambda *a:None)
    window.controller._receive({'status':'complete','job_id':active['job_id'],'session':window.controller.session,'result':result,'seconds':.1})
    assert window.document['jd']==jd_b and len(window.document['projects'])==6
    assert window.jd.toPlainText()==jd_a and window.document['comparison_jd']==jd_a
    assert window.controller.active['job_id']==queued['job_id']
    previous=json.loads((DATA/'drafts'/(old_id+'.json')).read_text(encoding='utf-8'))
    assert 'Late edit to the preceding resume.' in next(s['text'] for s in previous['document']['sections'] if s['key']=='projects')
    window.controller._receive({'status':'complete','job_id':active['job_id'],'session':window.controller.session,'result':initial,'seconds':.1})
    assert window.document['jd']==jd_b

    row=next(i for i,s in enumerate(window.document['sections']) if s['key']=='projects')
    window.sections.setCurrentRow(row)
    before=window.editor.toPlainText();marker='\nManual edited responsibility.'
    window.editor.moveCursor(QTextCursor.MoveOperation.End);window.editor.insertPlainText(marker)
    window.editor.undo();assert window.editor.toPlainText()==before
    window.editor.redo();assert window.editor.toPlainText()==before+marker
    window.refresh_preview();window.autosave()
    saved=load_draft(DATA/'last-draft.json')
    assert saved['resume']==str(source)
    assert saved['form_inputs']['resume']==str(DATA/'next candidate.docx')
    assert saved['document']['jd']==jd_b and saved['form_inputs']['jd']==jd_a
    window.close()
    restored=Window()
    assert restored.document['jd']==jd_b and restored.jd.toPlainText()==jd_a
    assert restored.resume.text()==str(DATA/'next candidate.docx')
    assert marker in next(s['text'] for s in restored.document['sections'] if s['key']=='projects')
    assert len(restored.document['projects'])==6
    restored.close()

    controller=JobController();controller._start=lambda job:setattr(controller,'active',job)
    payload={'jd':jd_a,'nested':{'value':1}}
    controller.submit('draft',payload);payload['nested']['value']=2
    assert controller.active['payload']['nested']['value']==1
    controller.submit('draft',payload);payload['nested']['value']=3
    assert controller.waiting['payload']['nested']['value']==2
    controller.close()
    checks={k:True for k in ['generation_jd_immutable','comparison_exports','pending_inputs','queued_snapshots',
        'completion_binding','stale_event_ignored','undo_redo','autosave_restart','deep_copy_payload','previous_edits_saved']}
    (DATA/'ui-check.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print(json.dumps(checks))


if __name__=='__main__':main()
