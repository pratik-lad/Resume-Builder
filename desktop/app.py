from __future__ import annotations

import copy
import html
import json
import os
import shutil
import time
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QByteArray
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QTextDocument
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                              QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
                              QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QStackedWidget,
                              QTextBrowser, QVBoxLayout, QWidget, QPlainTextDocumentLayout)

from desktop.edition import APP_ID, APP_LABEL
from desktop.bootstrap import DATA
from desktop.controller import JobController
from desktop.storage import atomic_json, load_json, load_draft
from desktop.draft import markdown


class OfflinePreview(QTextBrowser):
    def loadResource(self, kind, url):
        # Resume Markdown must not fetch images/files from user-supplied URLs.
        return QByteArray()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_LABEL)
        self.resize(1180, 790)
        self.document = None
        self.revision = 0
        self.loading = False
        self.draft_id = uuid.uuid4().hex
        self.section_documents = {}
        self.controller = JobController(self)
        self.controller.event.connect(self.job_event)
        self.sections = QListWidget()
        self.sections.setMaximumWidth(220)
        self.sections.currentRowChanged.connect(self.select_section)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Select a section to edit its text. Your changes appear in the preview and exports.")
        self.editor.textChanged.connect(self.edited)
        self.preview = OfflinePreview()
        self.preview.setOpenExternalLinks(False)
        self.preview.setOpenLinks(False)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.refresh_preview)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.autosave)
        self.resume = QLineEdit()
        self.resume.setReadOnly(True)
        self.resume.setPlaceholderText("Choose a text PDF or DOCX resume")
        browse = QPushButton("Choose resume")
        browse.clicked.connect(self.choose_resume)
        self.jd = QPlainTextEdit()
        self.jd.setPlaceholderText("Paste the complete job description here")
        self.jd.setMaximumHeight(145)
        self.jd.textChanged.connect(self.input_changed)
        self.generate = QPushButton("Generate resume")
        self.generate.setObjectName("primary")
        self.generate.clicked.connect(self.generate_draft)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.controller.cancel)
        self.cancel_button.hide()
        self.docx_button = QPushButton("Save DOCX")
        self.docx_button.setObjectName("primary")
        self.docx_button.clicked.connect(lambda: self.export("docx"))
        self.report_button = QPushButton("Save HTML report")
        self.report_button.clicked.connect(lambda: self.export("html"))
        self.edit_button = QPushButton("Edit resume")
        self.edit_button.setCheckable(True)
        self.edit_button.toggled.connect(self.toggle_edit)
        new = QPushButton("New resume")
        new.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.hide()
        self.status = QLabel("Choose a resume and paste the job description to begin.")
        self.status.setWordWrap(True)
        self.pages = QStackedWidget()
        start = QWidget()
        form = QVBoxLayout(start)
        title = QLabel("Create your next resume")
        title.setObjectName("title")
        form.addWidget(title)
        subtitle = QLabel("A complete fictional resume tailored to your job description. Works offline.")
        subtitle.setWordWrap(True)
        form.addWidget(subtitle)
        form.addSpacing(16)
        form.addWidget(QLabel("1. Choose your resume"))
        self.resume_row = QHBoxLayout()
        self.resume_row.addWidget(self.resume, 1)
        self.resume_row.addWidget(browse)
        form.addLayout(self.resume_row)
        form.addSpacing(16)
        form.addWidget(QLabel("2. Paste the job description"))
        self.jd.setMaximumHeight(16777215)
        form.addWidget(self.jd, 1)
        form.addWidget(QLabel("Quality comes first. Complete generation can take several minutes."))
        form.addWidget(self.generate)
        self.pages.addWidget(start)
        result = QWidget()
        result_layout = QVBoxLayout(result)
        actions = QHBoxLayout()
        for widget in (new, self.edit_button, self.docx_button, self.report_button):
            actions.addWidget(widget)
        result_layout.addLayout(actions)
        self.split = QSplitter()
        for widget in (self.sections, self.editor, self.preview):
            self.split.addWidget(widget)
        self.split.setSizes([160, 470, 470])
        self.sections.hide()
        self.editor.hide()
        result_layout.addWidget(self.split, 1)
        self.pages.addWidget(result)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(self.pages, 1)
        layout.addWidget(self.progress)
        footer = QHBoxLayout()
        footer.addWidget(self.status, 1)
        footer.addWidget(self.cancel_button)
        layout.addLayout(footer)
        self.setCentralWidget(root)
        self.setStyleSheet("""
            QMainWindow {background: #f4f6fa;}
            QLabel {color: #25344a; font-size: 13px;}
            QLabel#title {font-size: 26px; font-weight: 600;}
            QLineEdit, QPlainTextEdit, QTextBrowser, QListWidget {
                background: white; color: #202f43; border: 1px solid #ccd5e1;
                border-radius: 6px; padding: 8px; font-size: 14px;}
            QPushButton {padding: 10px 18px; border: 1px solid #c7d2e0;
                border-radius: 6px; background: white; color: #25344a;}
            QPushButton#primary {background: #245b98; color: white; border: none; font-weight: 600;}
            QPushButton:disabled {background: #e2e7ee; color: #78869a;}
        """)
        undo = QAction("Undo section edit", self, shortcut=QKeySequence.StandardKey.Undo)
        undo.triggered.connect(self.editor.undo)
        redo = QAction("Redo section edit", self, shortcut=QKeySequence.StandardKey.Redo)
        redo.triggered.connect(self.editor.redo)
        self.addActions([undo, redo])
        menu = self.menuBar().addMenu("Tools")
        verify = menu.addAction("Verify offline installation")
        verify.triggered.connect(lambda: self.controller.submit("verify", {}))
        logs = menu.addAction("Open logs folder")
        logs.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA / "logs"))))
        saved = load_draft(DATA / "last-draft.json")
        if saved:
            self.draft_id = saved.get("draft_id", self.draft_id)
            self.resume.setText(saved.get("resume", ""))
            self.jd.setPlainText(saved["document"].get("jd", ""))
            self.set_document(saved["document"])
            self.status.setText("Restored your saved draft. Exports include your current edits.")

    def choose_resume(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose resume", "", "Resumes (*.pdf *.docx)")
        if path:
            self.resume.setText(path)

    def generate_draft(self):
        if not self.resume.text() or not self.jd.toPlainText().strip():
            QMessageBox.information(self, "Resume and JD needed", "Choose a resume and paste the job description.")
            return
        self.autosave()
        self.controller.submit("draft", {"resume": self.resume.text(), "jd": self.jd.toPlainText(),
                                         "mode": "demo"}, self.revision)

    def toggle_edit(self, checked):
        self.sections.setVisible(checked)
        self.editor.setVisible(checked)
        self.edit_button.setText("Done editing" if checked else "Edit resume")

    def export(self, kind):
        if not self.document:
            QMessageBox.information(self, "Generate first", "Generate or restore a draft before exporting.")
            return
        self.autosave()
        extension = ".docx" if kind == "docx" else ".html"
        destination, _ = QFileDialog.getSaveFileName(self, "Save current resume", "resume" + extension,
                                                     "DOCX (*.docx)" if kind == "docx" else "HTML (*.html)")
        if destination:
            if not destination.lower().endswith(extension):
                destination += extension
            self.controller.submit("export", {"document": copy.deepcopy(self.document), "kind": kind,
                                              "destination": destination}, self.revision)

    def set_document(self, document):
        from desktop.project_document import sanitize
        cleaned = sanitize(document)
        document.clear()
        document.update(cleaned)
        self.loading = True
        self.document = document
        self.section_documents = {}
        self.sections.clear()
        for section in document["sections"]:
            self.sections.addItem(section["title"])
        self.loading = False
        self.sections.setCurrentRow(0)
        self.pages.setCurrentIndex(1)
        self.revision += 1
        self.autosave()
        self.refresh_preview()

    def select_section(self, row):
        if self.loading:
            return
        self.loading = True
        if self.document and row >= 0:
            if row not in self.section_documents:
                document = QTextDocument(self)
                document.setDocumentLayout(QPlainTextDocumentLayout(document))
                document.setPlainText(self.document["sections"][row]["text"])
                self.section_documents[row] = document
            self.editor.setDocument(self.section_documents[row])
        else:
            self.editor.setPlainText("")
        self.loading = False

    def edited(self):
        row = self.sections.currentRow()
        if self.loading or not self.document or row < 0:
            return
        self.document["sections"][row]["text"] = self.editor.toPlainText()
        self.revision += 1
        self.preview_timer.start(100)
        self.save_timer.start(500)

    def input_changed(self):
        if self.document and not self.loading:
            self.document["jd"] = self.jd.toPlainText()
            self.revision += 1
            self.save_timer.start(500)
            self.preview_timer.start(100)

    def refresh_preview(self):
        if not self.document:
            return
        content = markdown(self.document["sections"])
        lines = content.splitlines()
        if lines and not lines[0].startswith("#"):
            lines[0] = "# " + lines[0]
        # Preserve skill categories, contact details and project metadata as
        # separate lines instead of Markdown collapsing them into one paragraph.
        content = "\n".join(line + "  " if line.strip() and not line.startswith("#") else line for line in lines)
        if self.document.get("template_version") == "reference-2":
            from desktop.reference_layout import html
            self.preview.setHtml(html(self.document))
        else:
            self.preview.setMarkdown(content)
        self.preview.setToolTip("Your HTML report is recalculated from these edits when exported.")

    def autosave(self):
        if self.document:
            snapshot = {"draft_id": self.draft_id, "resume": self.resume.text(), "document": self.document}
            try:
                atomic_json(DATA / "drafts" / (self.draft_id + ".json"), snapshot)
                atomic_json(DATA / "last-draft.json", snapshot)
            except OSError as error:
                self.status.setText(f"Autosave failed: {error}. Use export to save your work.")

    def job_event(self, event):
        state = event["status"]
        if state == "started":
            self.progress.show()
            self.cancel_button.show()
            self.progress.setRange(0, 0)
            self.status.setText("Working in the background; the editor remains available.")
        elif state in {"progress", "queued"}:
            self.status.setText(event.get("message", "Working"))
        elif state == "complete":
            self.cancel_button.hide()
            self.progress.hide()
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            result = event["result"]
            if event["kind"] == "draft":
                self.draft_id = uuid.uuid4().hex
                self.set_document(result)
                self.status.setText(f"Resume ready in {event['seconds']:.1f}s. Review, edit or save your resume.")
            elif event["kind"] == "export":
                try:
                    path = Path(result["destination"])
                    temporary = path.with_name(path.name + ".resume-tmp-" + uuid.uuid4().hex)
                    shutil.copyfile(result["artifact"], temporary)
                    os.replace(temporary, path)
                    self.status.setText(f"Saved {path}")
                except OSError as error:
                    self.status.setText(f"Export exists in artifacts, but could not save to your chosen location: {error}")
            else:
                self.status.setText(f"Verified {result['verified']} offline assets.")
        elif state in {"error", "cancelled"}:
            self.cancel_button.hide()
            self.progress.hide()
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.status.setText(event.get("message", "Job failed"))
            if state == "error":
                QMessageBox.warning(self, "Unable to complete", event.get("message", "Job failed"))

    def closeEvent(self, event):
        self.autosave()
        self.controller.close()
        atomic_json(DATA / "last-session-metrics.json", {"peak_tree_rss_bytes": self.controller.peak_rss})
        event.accept()


def instance_mutex_name():
    name=APP_ID
    # Installer QA uses an explicit separate data directory and self-closing
    # window. Keep that test independent of a user's already-running app.
    if os.environ.get('RESUME_DESKTOP_SELF_TEST_MS') and os.environ.get('RESUME_DESKTOP_DATA'):
        import hashlib
        normal=Path(os.environ.get('LOCALAPPDATA',Path.home()))/APP_ID
        if DATA.resolve()!=normal.resolve():
            name += '.SelfTest.'+hashlib.sha256(str(DATA.resolve()).encode()).hexdigest()[:16]
    return name


def run():
    app = QApplication([])
    app.setApplicationName(APP_ID)
    app.setOrganizationName("ResumeOptimizer")
    handle = None
    if os.name == "nt":
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateMutexW(None, False, "Local\\" + instance_mutex_name())
        if ctypes.get_last_error() == 183:
            QMessageBox.information(None, "Already running", "Resume Optimizer Desktop is already open.")
            kernel.CloseHandle(handle)
            return
    window = Window()
    screen = app.primaryScreen()
    if screen:
        geometry = screen.availableGeometry()
        window.resize(min(1180, int(geometry.width() * .95)), min(790, int(geometry.height() * .9)))
    window.show()
    # Used by the installer integration test; no effect in normal launches.
    if os.environ.get("RESUME_DESKTOP_SELF_TEST_MS"):
        QTimer.singleShot(int(os.environ["RESUME_DESKTOP_SELF_TEST_MS"]), window.close)
        atomic_json(DATA / "logs/gui-startup.json", {"window_created": True, "mode": "demo", "app_id": APP_ID, "window_title": window.windowTitle(), "data_dir": str(DATA)})
    app.exec()
    if handle:
        kernel.CloseHandle(handle)
