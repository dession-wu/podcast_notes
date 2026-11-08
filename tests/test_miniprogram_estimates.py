from backend.mini.estimates import estimates


def test_ranges_queue_unknown_history_and_terminal():
    rows = [dict(id='a', episode='e', status='queued', timing='{}'), dict(id='b', episode='e', status='queued', timing='{}')]
    snapshot = (rows, [], {'e': {'duration_seconds': 600}})
    result = estimates(rows, snapshot, 'basic', now=1000)
    assert result['a']['remaining_lower_seconds'] == 108
    assert result['b']['remaining_upper_seconds'] == 648
    assert result['b']['queue_ahead'] == 1
    snapshot[2].clear()
    assert estimates(rows, snapshot, 'basic')['b']['basis'] == 'unknown'
    rows[0]['status'] = 'completed'
    assert estimates(rows, snapshot, 'basic')['a'] is None


def test_history_and_overdue():
    import json
    row = dict(id='a', episode='e', status='transcribing', timing=json.dumps({'transcription_started_at': 100}))
    history = [{'timing': json.dumps({'mode': 'basic', 'audio_duration_seconds': 600, 'transcription_seconds': 600})}]
    snapshot = ([row], history, {'e': {'duration_seconds': 600}})
    assert estimates([row], snapshot, 'basic', now=100)['a']['basis'] == 'history'
    value = estimates([row], snapshot, 'basic', now=2000)['a']
    assert value['overdue'] and value['remaining_upper_seconds'] is None


def test_api_estimates_consistent_private_and_survive_client_disconnect(tmp_path):
    from fastapi.testclient import TestClient
    from backend.mini.app import create_app
    app = create_app(tmp_path, development=True, demo=True, worker=False)
    store = app.state.store
    token_a, token_b = store.session('a'), store.session('b')
    auth_a, auth_b = {'Authorization': 'Bearer '+token_a}, {'Authorization': 'Bearer '+token_b}
    episode = store.put('episode', {'title': 'Private title', 'duration_seconds': 600})
    other = store.admit('b', episode, 'Other user private title')
    with TestClient(app) as client:
        response = client.post('/mini/tasks', headers=auth_a, json={'episode_id': episode, 'rights_confirmed': True})
        assert response.status_code == 202
        job = response.json()
        assert job['estimate']['queue_ahead'] == 1
        listing = client.get('/mini/tasks', headers=auth_a).json()['tasks']
        detail = client.get('/mini/tasks/'+job['id'], headers=auth_a).json()
        assert listing[0]['estimate'] == detail['estimate'] == job['estimate']
        assert [r['id'] for r in listing] == [job['id']]
        assert other['id'] not in str(listing)
        assert 'Other user private title' not in str(listing)
        assert 'owner' not in detail and 'episode' not in detail
        assert client.get('/mini/tasks/'+job['id'], headers=auth_b).status_code == 404
        assert client.get('/mini/tasks/'+job['id']).status_code == 401
    # The client is gone. The independent worker still consumes the durable queue.
    while (claimed := store.claim()) is not None:
        app.state.process(claimed)
    with TestClient(app) as client:
        detail = client.get('/mini/tasks/'+job['id'], headers=auth_a).json()
        assert detail['status'] == 'completed'
        assert detail['estimate'] is None
        assert detail['text']
        assert len(client.get('/mini/tasks', headers=auth_a).json()['tasks']) == 1


def test_unknown_or_overdue_predecessor_does_not_invent_queue_wait():
    import json
    first = dict(id='a', episode='unknown', status='transcribing', timing='{}')
    second = dict(id='b', episode='known', status='queued', timing='{}')
    snapshot = ([first, second], [], {'known': {'duration_seconds': 600}})
    value = estimates([second], snapshot, 'dialogue', now=1000)['b']
    assert value['queue_ahead'] == 1 and value['remaining_upper_seconds'] is None
    first.update(episode='known', timing=json.dumps({'transcription_started_at': 100}))
    value = estimates([first, second], snapshot, 'dialogue', now=1000)
    assert value['a']['overdue'] and value['b']['remaining_upper_seconds'] is None


def test_history_ignores_other_modes_and_uses_median_and_detected_duration():
    import json
    row = dict(id='a', episode='e', status='transcribing', timing=json.dumps({'audio_duration_seconds': 120, 'transcription_started_at': 100}))
    history = [{'timing': json.dumps({'mode': mode, 'audio_duration_seconds': 120, 'transcription_seconds': seconds})}
               for mode, seconds in [('basic', 900), ('dialogue', 12), ('dialogue', 12), ('dialogue', 200)]]
    value = estimates([row], ([row], history, {'e': {'duration_seconds': 9000}}), 'dialogue', now=100)['a']
    assert value['basis'] == 'history'
    assert value['remaining_upper_seconds'] == 76  # ceil(1.8 * (30 + .1 * 120))

