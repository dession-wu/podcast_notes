"""Dialogue contract, legacy migration, ownership and worker handoff regression checks."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.mini.app import create_app
from backend.mini.dialogue import parse_sentences, format_text
from backend.mini.store import Store


def test_timed_turns_preserve_content_and_repeated_speaker():
    segments = parse_sentences([{'sentence_info': [
        {'start': 1250, 'end': 3800, 'text': '你好。', 'spk': 8},
        {'start': 4100, 'end': 5900, 'text': '欢迎。', 'spk': 2},
        {'start': 6200, 'end': 8100, 'text': '继续聊。', 'spk': 8},
        {'start': 3601000, 'end': 3602000, 'text': '结束。'},
    ]}])
    assert [s['speaker'] for s in segments] == ['说话人 1', '说话人 2', '说话人 1', None]
    assert segments[0]['start_time'] == 1.25
    assert segments[1]['end_time'] == 5.9
    text = format_text(segments)
    assert '[00:01] 说话人 1\n你好。' in text
    assert '[01:00:01]\n结束。' in text


@pytest.mark.parametrize('sentence', [
    {'text': '无时间'}, {'text': '倒序', 'start': 100, 'end': 0},
    {'text': '非有限', 'start': 0, 'end': float('inf')},
])
def test_missing_timing_is_rejected_instead_of_fabricated(sentence):
    with pytest.raises(ValueError, match='时间戳'):
        parse_sentences([{'sentence_info': [sentence]}])
    with pytest.raises(ValueError, match='语句'):
        parse_sentences([{'text': '整段无时间'}])


def test_existing_database_migrates_without_losing_text(tmp_path):
    path = tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, owner TEXT, episode TEXT, title TEXT, day TEXT, created REAL, status TEXT, text TEXT DEFAULT '', error TEXT DEFAULT '')")
        db.execute("INSERT INTO jobs VALUES ('old','a','ep','旧记录','2026-11-02',1,'completed','原文','')")
    store = Store(path)
    assert store.job('old', 'a')['text'] == '原文'
    assert json.loads(store.job('old', 'a')['segments']) == []
    assert json.loads(store.job('old', 'a')['timing']) == {}
    Store(path)  # migration is repeatable


def test_worker_structured_result_reaches_owned_reader_export_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv('MINI_TRANSCRIPT_MODE', 'dialogue')
    app = create_app(tmp_path, development=True, demo=False, worker=False)
    monkeypatch.setenv('MINI_TRANSCRIPT_MODE', 'basic')  # Running app must retain its configured mode.
    segments = parse_sentences([{'sentence_info': [
        {'start': 1200, 'end': 2500, 'text': '对话原文。', 'spk': 0},
        {'start': 3000, 'end': 4300, 'text': '接着讨论。', 'spk': 1},
    ]}])
    def run(args, **kwargs):
        if args[0] == 'ffprobe':
            return type('Probe', (), {'stdout': '5'})()
        output = Path(args[-1])
        assert kwargs['env']['MINI_TRANSCRIPT_MODE'] == 'dialogue'
        output.write_text(format_text(segments), encoding='utf-8')
        output.with_suffix('.segments.json').write_text(json.dumps({'segments': segments}), encoding='utf-8')
    with TestClient(app) as client:
        def auth(name):
            return {'Authorization': 'Bearer '+client.post('/mini/login', json={'code': 'dev:'+name*12}).json()['token']}
        alice, bob = auth('alice'), auth('bob')
        ep = app.state.store.put('episode', {'title': '双人对话', 'audio_url': 'https://example.com/audio.wav'})
        key = client.post('/mini/tasks', headers=alice, json={'episode_id': ep, 'rights_confirmed': True}).json()['id']
        with patch('backend.mini.app.fetch'), patch('backend.mini.app.subprocess.run', side_effect=run):
            app.state.process(app.state.store.claim())
        result = client.get('/mini/tasks/'+key, headers=alice).json()
        assert result['status'] == 'completed'
        assert result['segments'] == segments
        assert result['timing']['mode'] == 'dialogue'
        assert result['timing']['audio_duration_seconds'] == 5
        assert result['timing']['elapsed_seconds'] >= result['timing']['processing_seconds'] >= 0
        assert result['timing']['download_seconds'] >= 0
        assert result['timing']['transcription_seconds'] >= 0
        assert client.get('/mini/health').json()['transcript_mode'] == 'dialogue'
        assert client.get('/mini/tasks', headers=alice).json()['tasks'][0]['timing'] == result['timing']
        assert client.get('/mini/tasks/'+key+'/export', headers=alice).text == '\ufeff'+format_text(segments)
        assert client.get('/mini/tasks/'+key, headers=bob).status_code == 404
        assert client.get('/mini/tasks/'+key+'/export', headers=bob).status_code == 404
        assert not list(tmp_path.glob('*.json'))
        assert client.delete('/mini/tasks/'+key, headers=alice).status_code == 204
        row = app.state.store.job(key, app.state.store.owner(alice['Authorization'][7:]))
        assert row['text'] == '' and json.loads(row['segments']) == []
        assert json.loads(row['timing']) == {}


def test_dialogue_mode_cannot_silently_complete_with_basic_output(tmp_path, monkeypatch):
    monkeypatch.setenv('MINI_TRANSCRIPT_MODE', 'dialogue')
    app = create_app(tmp_path, development=True, demo=False, worker=False)
    store = app.state.store
    ep = store.put('episode', {'title': '测试', 'audio_url': 'https://example.com/a.wav'})
    job = store.admit('owner', ep, '测试')
    def run(args, **kwargs):
        if args[0] == 'ffprobe':
            return type('Probe', (), {'stdout': '5'})()
        Path(args[-1]).write_text('Legacy single block output', encoding='utf-8')
    with patch('backend.mini.app.fetch'), patch('backend.mini.app.subprocess.run', side_effect=run):
        app.state.process(store.claim())
    result = store.job(job['id'], 'owner')
    assert result['status'] == 'failed'
    assert '对话模式' in result['error']
    assert json.loads(result['timing'])['finished_at'] > 0
