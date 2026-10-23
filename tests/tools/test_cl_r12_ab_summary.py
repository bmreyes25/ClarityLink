"""CL-HONDA-111-02: the CL-R12 A/B summarizer must not over-read noisy runs."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("summ", REPO / "tools/summarize_cl_r12_ab.py")
summ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summ)


def result(fps, p50, p95, p99, dropped, fd_base=46, fd_final=49, offered=900):
    return ("I/ClarityLinkR12B( 1): R12B_RESULT mode=short error=null offered=%d delivered_fps=%s "
            "dropped=%d latency_p50_ms=%s latency_p95_ms=%s latency_p99_ms=%s source_fd_base=%d "
            "source_fd_final=%d host_fd_base=32 host_fd_final=32 pixel_mismatches=0 transport_errors=0\n"
            % (offered, fps, dropped, p50, p95, p99, fd_base, fd_final))


def write(dirpath, variant, index, **kw):
    suffix = "" if index == 1 else "-r%d" % index
    (dirpath / ("perf-%s%s-logcat.txt" % (variant, suffix))).write_text(result(**kw))


def fill(tmp_path, base_fps, cand_fps):
    for i, (b, c) in enumerate(zip(base_fps, cand_fps), 1):
        write(tmp_path, "baseline", i, fps=b, p50=30, p95=50, p99=60, dropped=100)
        write(tmp_path, "optimized", i, fps=c, p50=30, p95=50, p99=60, dropped=100)


def test_single_pair_is_never_called_a_difference(tmp_path):
    fill(tmp_path, [20.0], [14.9])
    verdicts = {k: v["verdict"] for k, v in summ.summarize(tmp_path)["metrics"].items()}
    assert set(verdicts.values()) == {"INSUFFICIENT_RUNS"}


def test_overlapping_ranges_are_not_distinguishable(tmp_path):
    fill(tmp_path, [24.6, 20.0, 22.0], [25.6, 14.9, 21.0])
    assert summ.summarize(tmp_path)["metrics"]["delivered_fps"]["verdict"] == "NOT_DISTINGUISHABLE"


def test_separated_ranges_are_reported_in_the_right_direction(tmp_path):
    fill(tmp_path, [25.0, 26.0, 27.0], [14.0, 15.0, 16.0])
    m = summ.summarize(tmp_path)["metrics"]["delivered_fps"]
    assert m["verdict"] == "CANDIDATE_WORSE" and m["baseline_median"] == 26.0
    fill(tmp_path, [14.0, 15.0, 16.0], [25.0, 26.0, 27.0])
    assert summ.summarize(tmp_path)["metrics"]["delivered_fps"]["verdict"] == "CANDIDATE_BETTER"


def test_lower_is_better_for_latency_and_drops(tmp_path):
    for i, (b, c) in enumerate(zip([30, 31, 32], [50, 51, 52]), 1):
        write(tmp_path, "baseline", i, fps=25, p50=b, p95=b, p99=b, dropped=10)
        write(tmp_path, "optimized", i, fps=25, p50=c, p95=c, p99=c, dropped=10)
    m = summ.summarize(tmp_path)["metrics"]
    assert m["latency_p95_ms"]["verdict"] == "CANDIDATE_WORSE"
    assert m["drop_fraction"]["verdict"] == "NOT_DISTINGUISHABLE"


def test_runs_without_a_result_line_are_ignored_and_integrity_is_counted(tmp_path):
    (tmp_path / "perf-baseline-logcat.txt").write_text("no result here\n")
    write(tmp_path, "optimized", 1, fps=25, p50=1, p95=1, p99=1, dropped=0)
    s = summ.summarize(tmp_path)
    assert s["integrity"]["baseline"]["runs"] == 0 and s["integrity"]["candidate"]["runs"] == 1


def test_the_summarizer_never_decides_an_acceptance_gate():
    text = (REPO / "tools/summarize_cl_r12_ab.py").read_text()
    assert "PERFORMANCE_GATE" not in text and "exit(1)" not in text


def test_non_overlapping_but_tiny_differences_are_labelled_negligible(tmp_path):
    fill(tmp_path, [15.066, 15.133, 15.249], [15.033, 15.016, 15.046])   # a real CI receipt: 0.7%
    m = summ.summarize(tmp_path)["metrics"]["delivered_fps"]
    assert m["verdict"] == "CANDIDATE_WORSE_NEGLIGIBLE"
    fill(tmp_path, [20.0, 20.1, 20.2], [14.0, 14.1, 14.2])
    assert summ.summarize(tmp_path)["metrics"]["delivered_fps"]["verdict"] == "CANDIDATE_WORSE"


def test_a_descriptor_count_difference_is_material_even_from_a_zero_baseline(tmp_path):
    for i in (1, 2, 3):
        write(tmp_path, "baseline", i, fps=25, p50=1, p95=1, p99=1, dropped=0, fd_base=46, fd_final=46)
        write(tmp_path, "optimized", i, fps=25, p50=1, p95=1, p99=1, dropped=0, fd_base=46, fd_final=49)
    assert summ.summarize(tmp_path)["metrics"]["source_fd_delta"]["verdict"] == "CANDIDATE_WORSE"
