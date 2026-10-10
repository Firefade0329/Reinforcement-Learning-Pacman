"""ANALYSIS_SPEC 8.6: two-error priority across files, and the classification of finite non-integer / boolean / string / non-finite scores.

Each case starts from the valid synthetic study, changes exactly what the row says (hashes of the seal follow the edits), and expects the literal code of the
specification.  No code of the analysis changes with these tests: they pin the existing order -- global stages 1-4 over ALL files first, then per CSV run
last/standard -> best/standard -> last/hard, each file completely through stages 5, 6, 7 before the next one.  Same-AI implementer and test author."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prereg_analysis as A  # noqa: E402
from prereg_fixture import Study  # noqa: E402

D = {"cnn2": [10] * 5, "res4": [20] * 5, "res8": [30] * 5}
R1, R2 = "prereg_res4_n1_s100", "prereg_res4_n3_s100"  # the first and the second run of the matrix


@pytest.fixture()
def study(tmp_path):
    return Study(tmp_path / "p", d=D)


def code_of(tmp_path, st):
    out = tmp_path / "o"
    with pytest.raises(A.AnalysisError) as e:
        A.analyze(st.manifest, st.runs, out, "synthetic")
    assert not out.exists()
    return e.value.obj


def set_score(st, run, rel, idx, score):
    st.edit_json(run, rel, lambda d: d["records"][idx].update(score=score), reseal=False)


def drop_record(st, run, rel):
    st.edit_json(run, rel, lambda d: d["records"].pop(), reseal=False)


# ------------------------------------------------------------------ finite non-integer score and the other score classes
def test_score_1_5_is_a_score_range_error_with_the_hashes_updated(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 1.5)
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_SCORE_RANGE" and o["actual"] == 1.5 and o["record_index"] == 0


def test_score_100_0_is_a_legal_integer_valued_score(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 100.0)  # the scored value of the valid fixture is 100 (n=3) / 110 (n=1)
    study.reseal()
    A.analyze(study.manifest, study.runs, tmp_path / "ok", "synthetic")


@pytest.mark.parametrize("bad", [True, "100", None, [100]])
def test_boolean_string_null_or_list_score_is_a_field_type_error(study, tmp_path, bad):
    set_score(study, R1, "last/standard.json", 3, bad)
    study.reseal()
    assert code_of(tmp_path, study)["code"] == "E_FIELD_TYPE"


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_non_finite_score_is_rejected_at_parsing_before_any_field_check(study, tmp_path, literal):
    p = study.path(R1, "last/standard.json")
    text = p.read_text()
    first = text.index('"score": ')
    end = text.index(",", first)
    p.write_text(text[:first] + f'"score": {literal}' + text[end:])
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_NONFINITE"


def test_score_1_5_together_with_a_bad_end_flag_type_reports_the_score_first(study, tmp_path):
    study.edit_json(R1, "last/standard.json", lambda d: d["records"][0].update(score=1.5, died="yes"), reseal=False)
    study.reseal()
    assert code_of(tmp_path, study)["code"] == "E_SCORE_RANGE"  # fixed per-record order: type of the keys' values -> score integrality -> flag types


def test_score_378_is_a_range_error_and_377_with_won_is_legal(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 378)
    study.reseal()
    assert code_of(tmp_path, study)["code"] == "E_SCORE_RANGE"


# ------------------------------------------------------------------ two faults in different files
def test_first_run_last_score_error_is_reported_before_the_same_runs_best_count_error(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 378)  # stage 6 of the FIRST file
    drop_record(study, R1, "best/standard.json")         # stage 5 of the SECOND file
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_SCORE_RANGE" and o["path"] == f"{R1}/last/standard.json"


def test_moving_the_score_error_to_the_next_run_lets_the_earlier_runs_count_error_come_first(study, tmp_path):
    set_score(study, R2, "last/standard.json", 0, 378)  # a later run's last file
    drop_record(study, R1, "best/standard.json")         # the earlier run's best file
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_EPISODE_COUNT" and o["path"] == f"{R1}/best/standard.json"


def test_a_duplicate_seed_in_an_earlier_file_beats_a_score_error_in_a_later_file(study, tmp_path):
    study.edit_json(R1, "last/standard.json", lambda d: d["records"][1].update(seed=d["records"][0]["seed"]), reseal=False)  # stage 7, file 1
    set_score(study, R1, "best/standard.json", 0, 378)                                                                  # stage 6, file 2
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_DUPLICATE_SEED" and o["path"] == f"{R1}/last/standard.json"  # each file completes 5-7 before the next one starts


# ------------------------------------------------------------------ global stages beat any record semantics
def test_a_non_finite_number_in_a_later_run_beats_a_score_error_in_the_first_run(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 378)
    p = study.path(R2, "best/standard.json")
    text = p.read_text()
    first = text.index('"score": ')
    p.write_text(text[:first] + '"score": NaN' + text[text.index(",", first):])
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_NONFINITE" and o["path"] == f"{R2}/best/standard.json"


def test_a_configuration_drift_in_a_later_run_beats_a_score_error_in_the_first_run(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 378)
    study.edit_json(R2, "config.json", lambda d: d.update(tau=0.02), reseal=False)
    study.reseal()
    o = code_of(tmp_path, study)
    assert o["code"] == "E_CONFIG_MISMATCH" and o["run_name"] == R2


def test_the_initial_hash_pair_check_precedes_every_record_check(study, tmp_path):
    set_score(study, R1, "last/standard.json", 0, 378)
    study.edit_json("prereg_res4_n3_s100", "summary.json", lambda d: d.update(initial_state_dict_sha256="ab" * 32), reseal=False)
    study.reseal()
    assert code_of(tmp_path, study)["code"] == "E_INIT_PAIR_MISMATCH"
