import pytest
from google import genai
from google.auth.credentials import AnonymousCredentials
from google.genai import types

from swarmgate import llm
from swarmgate.e1 import runner

FLEX = {"provider": "google", "vertexai": True, "location": "global", "model": "m", "flex": True}


class Captured:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class Busy(Exception):
    code = 503


def test_flex_sends_both_headers_and_the_server_deadline_comes_first(monkeypatch):
    monkeypatch.setattr(genai, "Client", Captured)
    options = llm._genai_client(FLEX).kwargs["http_options"]
    assert options.headers == {**llm.FLEX_HEADERS, "X-Server-Timeout": str(llm.FLEX_SERVER_TIMEOUT)}
    assert options.timeout / 1000 > llm.FLEX_SERVER_TIMEOUT
    assert llm._genai_client({**FLEX, "flex": False}).kwargs["http_options"] is None


def test_flex_needs_vertex_and_the_global_location():
    for spec in ({**FLEX, "location": "us-central1"}, {**FLEX, "vertexai": False}):
        with pytest.raises(ValueError):
            llm._genai_client(spec)


def test_the_sdk_keeps_the_flex_headers_and_both_deadlines():
    client = genai.Client(vertexai=True, project="p", location="global", credentials=AnonymousCredentials(),
                          http_options=llm._flex_options())
    request = client._api_client._build_request("post", "publishers/google/models/m:generateContent", {})
    assert {k: request.headers[k] for k in llm.FLEX_HEADERS} == llm.FLEX_HEADERS
    assert request.headers["X-Server-Timeout"] == str(llm.FLEX_SERVER_TIMEOUT)
    assert request.timeout == llm.FLEX_SERVER_TIMEOUT + llm.FLEX_CLIENT_MARGIN


def test_google_turns_record_the_traffic_type(monkeypatch):
    usage = types.GenerateContentResponseUsageMetadata(prompt_token_count=10, candidates_token_count=2,
                                                       thoughts_token_count=5, traffic_type="ON_DEMAND_FLEX")
    reply = types.GenerateContentResponse(usage_metadata=usage, candidates=[types.Candidate(
        content=types.Content(role="model", parts=[types.Part(text="ls")]), finish_reason="STOP")])

    class Fake(Captured):
        models = property(lambda self: self)

        def generate_content(self, **kwargs):
            return reply

    monkeypatch.setattr(genai, "Client", Fake)
    turn = llm.GoogleClient(FLEX).step("s", [{"role": "user", "text": "u"}], tools=False)
    assert turn.text == "ls" and turn.meta["usage"] == {"input": 10, "output": 7, "traffic": "ON_DEMAND_FLEX"}


def test_jobs_are_tried_as_often_as_the_spec_allows(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)
    calls = []

    def work(client, cell):
        calls.append(1)
        if len(calls) < 8:
            raise Busy()
        return {"text": "ok"}

    out, job = tmp_path / "r.jsonl", [("m", "c0", {})]
    assert runner.run_jobs({"m": {}}, job, work, out, clients={"m": None}) == {"todo": 1, "done": 0, "failed": 1}
    assert len(calls) == 6
    assert runner.run_jobs({"m": {"attempts": 12}}, job, work, out, clients={"m": None})["done"] == 1
    assert len(calls) == 8
