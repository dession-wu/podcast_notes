"""Local diagnostic reports must remain read-only and omit private content."""
import json
import sqlite3

from backend.mini.store import Store
from scripts.diagnose_miniprogram_results import inspect_database, describe_process
from pathlib import Path


def test_process_report_never_returns_command_line_or_secret():
    row = {'ProcessId': 12, 'ParentProcessId': 10,
           'CommandLine': 'python E:\\podnotes\\podnotes-server\\scripts\\run_miniprogram_server.py --mode dialogue --secret PRIVATE_CREDENTIAL'}
    report = describe_process(row, Path('E:/podnotes/podnotes-server'))
    assert report['explicit_mode'] == 'dialogue'
    assert report['references_this_project'] is True
    assert 'PRIVATE_CREDENTIAL' not in json.dumps(report)
    assert 'CommandLine' not in report
    unknown = describe_process({'CommandLine': 'python unrelated.py --secret PRIVATE_CREDENTIAL'}, Path('/tmp'))
    assert unknown['roles'] == ['unclassified Python process']
    assert 'PRIVATE_CREDENTIAL' not in json.dumps(unknown)


def test_task_diagnostic_omits_text_and_sessions_and_does_not_change_rows(tmp_path):
    path = tmp_path/'mini.sqlite3'
    store = Store(path)
    secret = store.session('owner')
    job = store.admit('owner', 'episode', 'Sample')
    store.update(job['id'], 'completed', text='PRIVATE TRANSCRIPT BODY',
                 segments=[{'start_time': 1, 'end_time': 2, 'speaker': '说话人 1', 'text': 'PRIVATE SEGMENT BODY'}],
                 timing={'mode': 'dialogue', 'elapsed_seconds': 4})
    with sqlite3.connect(path) as db:
        before = list(db.iterdump())
    report = inspect_database(path)
    with sqlite3.connect(path) as db:
        assert list(db.iterdump()) == before
    assert report[0]['segment_count'] == 1
    assert report[0]['timing']['elapsed_seconds'] == 4
    rendered = json.dumps(report)
    assert secret not in rendered
    assert 'PRIVATE TRANSCRIPT BODY' not in rendered
    assert 'PRIVATE SEGMENT BODY' not in rendered
