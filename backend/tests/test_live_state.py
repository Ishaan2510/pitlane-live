from app.services import fastf1_service as mod


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


def _fresh():
    return mod.FastF1Service()


def test_no_token_is_unavailable(monkeypatch):
    monkeypatch.delenv('OPENF1_TOKEN', raising=False)
    assert _fresh().get_live_full_state()['status'] == 'unavailable'


def test_rejected_token_is_unavailable_and_cached(monkeypatch):
    monkeypatch.setenv('OPENF1_TOKEN', 't')
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(headers)
        return _Resp(401, {'detail': 'no'})

    monkeypatch.setattr(mod.requests, 'get', fake_get)
    svc = _fresh()
    assert svc.get_live_full_state()['status'] == 'unavailable'
    assert svc.get_live_full_state()['status'] == 'unavailable'
    assert calls == [{'Authorization': 'Bearer t'}]   # second call served from the 5s cache


def test_empty_session_list_is_unavailable(monkeypatch):
    monkeypatch.setenv('OPENF1_TOKEN', 't')
    monkeypatch.setattr(mod.requests, 'get', lambda *a, **k: _Resp(200, []))
    assert _fresh().get_live_full_state()['status'] == 'unavailable'
