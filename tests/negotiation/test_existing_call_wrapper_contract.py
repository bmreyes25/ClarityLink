"""SYNTHETIC_TEST_VALUE wrapper semantics; no Honda code is executed."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))
from wrapper_contract import serialize_stock_response  # noqa: E402


def setup_case(**options):
    request = {"streams": [{"type": 110}, {"type": 111, "opaque": "keep"}]}
    response = {"streams": [{"type": 110, "stock": "same"}]}
    audio = {"active": True, "volume": 0.5}
    calls, prepared, commits, rollbacks = [], [], [], []

    def serializer(value):
        calls.append(value)
        return (0xC8, 0)

    def prepare(identity, generation):
        prepared.append((identity, generation))
        if options.get("prepare_error"):
            raise RuntimeError("synthetic prepare failure")
        return {"listener": object()}

    def build_entry(request_value, response_value, state):
        if options.get("entry_error"):
            raise RuntimeError("synthetic entry failure")
        return {"type": 111, "dataPort": 6000, "owner": "project"}

    def append_entry(response_value, entry):
        if options.get("append_error"):
            raise RuntimeError("synthetic atomic append failure")
        response_value["streams"].append(entry)

    def commit(state):
        commits.append(state)

    def rollback(state):
        rollbacks.append(state)

    if options.get("serializer_result"):
        serializer = lambda value: (calls.append(value), options["serializer_result"])[1]
    result = serialize_stock_response(
        request=request,
        response=response,
        is_setup=options.get("is_setup", True),
        setup_status=options.get("setup_status", 0),
        identity=options.get("identity", object()),
        generation=options.get("generation", 1),
        serializer=serializer,
        project_enabled=options.get("project_enabled", True),
        prepare=prepare,
        build_entry=build_entry,
        append_entry=append_entry,
        commit=commit,
        rollback=rollback,
        is_current_generation=options.get("is_current", lambda _identity, _generation: True),
    )
    return result, request, response, audio, calls, prepared, commits, rollbacks


def test_unrelated_or_disabled_response_delegates_exact_stock_once():
    result, _, response, _, calls, prepared, commits, rollbacks = setup_case(is_setup=False)
    assert result.response is response and calls == [response]
    assert not prepared and not commits and not rollbacks
    result, _, response, _, calls, prepared, commits, rollbacks = setup_case(project_enabled=False)
    assert result.response is response and calls == [response]
    assert not prepared and not commits and not rollbacks


def test_project_prepare_and_entry_precede_one_stock_serializer_call():
    result, request, response, audio, calls, prepared, commits, rollbacks = setup_case()
    assert result.response is response and calls == [response]
    assert prepared == [(result.identity, 1)] and len(commits) == 1 and not rollbacks
    assert response["streams"][0] == {"type": 110, "stock": "same"}
    assert response["streams"][1]["type"] == 111
    assert request == {"streams": [{"type": 110}, {"type": 111, "opaque": "keep"}]}
    assert audio == {"active": True, "volume": 0.5}


def test_project_prepare_or_entry_failure_fails_open_and_rolls_back():
    for options in ({"prepare_error": True}, {"entry_error": True}):
        result, _, response, _, calls, _, commits, rollbacks = setup_case(**options)
        assert result.response is response and calls == [response]
        assert response["streams"] == [{"type": 110, "stock": "same"}]
        assert not commits and len(rollbacks) == 1


def test_serializer_failure_rolls_back_without_changing_stock_result():
    expected = (0x1F4, -7)
    result, _, response, _, calls, _, commits, rollbacks = setup_case(serializer_result=expected)
    assert result.serializer_result == expected
    assert calls == [response] and not commits and len(rollbacks) == 1


def test_stale_generation_skips_prepare_and_never_commits():
    result, _, response, _, calls, prepared, commits, rollbacks = setup_case(
        is_current=lambda _identity, _generation: False,
    )
    assert result.response is response and calls == [response]
    assert not prepared and not commits and not rollbacks


def test_generation_superseded_before_append_rolls_back_without_response_mutation():
    checks = [True, False]
    result, _, response, _, calls, _, commits, rollbacks = setup_case(
        is_current=lambda _identity, _generation: checks.pop(0),
    )
    assert result.response is response and calls == [response]
    assert response["streams"] == [{"type": 110, "stock": "same"}]
    assert not commits and len(rollbacks) == 1


def test_generation_superseded_at_commit_cannot_activate_child():
    checks = [True, True, False]
    result, _, response, _, calls, _, commits, rollbacks = setup_case(
        is_current=lambda _identity, _generation: checks.pop(0),
    )
    assert result.response is response and result.project_extended
    assert calls == [response] and not commits and len(rollbacks) == 1


def test_serializer_exception_rolls_back_then_propagates_without_retry():
    calls, rolled_back = [], []
    request = {"streams": []}
    response = {"streams": [{"type": 110}]}
    def serializer(value):
        calls.append(value)
        raise OSError("synthetic serializer failure")
    try:
        serialize_stock_response(
            request=request, response=response, is_setup=True, setup_status=0,
            identity="opaque", generation=1, serializer=serializer,
            project_enabled=True, prepare=lambda *_: "project-state",
            build_entry=lambda *_: {"type": 111},
            append_entry=lambda target, entry: target["streams"].append(entry),
            commit=lambda _state: None, rollback=rolled_back.append,
        )
    except OSError:
        pass
    else:
        raise AssertionError("stock serializer exception must propagate")
    assert calls == [response] and rolled_back == ["project-state"]


def test_duplicate_setup_prepare_rejection_fails_open_and_stock_calls_once():
    result, _, response, _, calls, _, commits, rollbacks = setup_case(prepare_error=True)
    assert result.response is response and calls == [response]
    assert response["streams"] == [{"type": 110, "stock": "same"}]
    assert not commits and len(rollbacks) == 1


def test_append_failure_before_mutation_rolls_back_and_delegates_stock():
    result, _, response, _, calls, _, commits, rollbacks = setup_case(append_error=True)
    assert result.response is response and calls == [response]
    assert response["streams"] == [{"type": 110, "stock": "same"}]
    assert not commits and len(rollbacks) == 1


def test_setup_failure_skips_project_but_delegates_stock_serializer_once():
    result, _, response, _, calls, prepared, commits, rollbacks = setup_case(setup_status=-1)
    assert result.response is response and calls == [response]
    assert not prepared and not commits and not rollbacks


def test_two_concurrent_contexts_do_not_share_transaction_identity():
    # The adapter stores identity/generation in call-local state, never globals.
    ids = [object(), object()]
    results = []
    import threading
    barrier = threading.Barrier(2)

    def run(identity, generation):
        barrier.wait()
        result, *_ = setup_case(identity=identity, generation=generation)
        results.append(result)

    threads = [threading.Thread(target=run, args=(ids[0], 2)),
               threading.Thread(target=run, args=(ids[1], 9))]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert {(result.identity, result.generation) for result in results} == {(ids[0], 2), (ids[1], 9)}
