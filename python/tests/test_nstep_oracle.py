"""End-to-end check of the n-step target pipeline against an independent oracle (see nstep_oracle.py):
real ``collect_step`` -> ``NStepReplay`` -> ``sample`` -> ``td_target`` on scripted toy MDPs.

Implementer and verifier of this test are the same person (the model that wrote the code under test); the expected
numbers come from the preregistration's hand computations (data/nstep_oracle_cases.json), cross-checked by an
exact-arithmetic re-derivation.  An independent human review is still required (reviewer / review_date fields in the
JSON are intentionally empty)."""
from fractions import Fraction

import pytest

import nstep_harness as H
import nstep_oracle as O
import pacman_rl.dqn as dqn
from nstep_mutants import MUTANTS

CASES = H.CASES["cases"]
GAMMA = H.CASES["gamma"]


def frac(x):
    return Fraction(x)


@pytest.mark.parametrize("quant", [False, True], ids=["float", "uint8"])
@pytest.mark.parametrize("n", ["1", "3"])
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_hand_computed_literals_match_pipeline_and_oracle(case, n, quant):
    """Three-way agreement: hand literal == independent exact oracle == real pipeline (both Double and plain max)."""
    exp = case["expected"][n]
    for double, col in ((True, 5), (False, 6)):
        lit = [(s[0], s[1], frac(s[2]), frac(s[3]), s[4], frac(s[col])) for s in exp["samples"]]
        want, want_counts = H.expected(case["envs"], case["q_online"], case["q_target"], int(n), GAMMA, double)
        assert want == sorted(lit) and want_counts == exp["counts"], "oracle disagrees with the hand-computed literal"
        actual, counts, _, replay = H.run_pipeline(case["envs"], case["q_online"], case["q_target"], int(n), GAMMA, double, quant)
        assert actual == sorted(lit), "pipeline disagrees with the hand-computed literal"
        assert counts == exp["counts"]


def test_double_dqn_uses_online_argmax_with_target_value():
    """The fixture the preregistration calls out: online prefers a0, target values a1 higher -> 4 and 4.25, not 11 and 6.75."""
    case = CASES[0]
    for n, (right, wrong) in (("1", (4.0, 11.0)), ("3", (4.25, 6.75))):
        double, *_ = H.run_pipeline(case["envs"], case["q_online"], case["q_target"], int(n), GAMMA, True)[:1]
        plain, *_ = H.run_pipeline(case["envs"], case["q_online"], case["q_target"], int(n), GAMMA, False)[:1]
        assert float(double[0][5]) == right and float(plain[0][5]) == wrong


def test_truncation_bootstraps_from_the_real_final_state_not_the_reset_state():
    case = next(c for c in CASES if c["name"] == "truncated_short_chain")
    samples, *_ = H.run_pipeline(case["envs"], case["q_online"], case["q_target"], 3, GAMMA, True)
    by_state = {s[0]: s for s in samples}
    assert by_state[0][4] == 2 and by_state[1][4] == 2  # next state is the real final state 2, never the reset state 5
    assert float(by_state[0][5]) == 4.0 and float(by_state[1][5]) == 6.0  # 2 + .25*8 and 2 + .5*8 (reset state would give 27 / 52)
    assert float(by_state[0][3]) == GAMMA ** 2 and float(by_state[1][3]) == GAMMA  # gamma^h with the real horizon h = 2 / 1


@pytest.mark.parametrize("quant", [False, True], ids=["float", "uint8"])
@pytest.mark.parametrize("n", [1, 2, 3, 5])
@pytest.mark.parametrize("double", [True, False], ids=["double", "plain"])
def test_random_interleaved_streams_match_the_oracle_exactly(n, double, quant):
    """Three environments, random episode lengths, terminations and truncations, unique state ids: sample set, sample
    timing (replay size after every round), episode isolation and targets all equal the exact oracle (gamma = 1/2)."""
    for seed in range(12):
        envs, qo, qt = O.random_case(seed)
        H.run_and_compare(envs, qo, qt, n, GAMMA, double, quant)


def test_gamma_099_matches_to_float32_precision():
    for seed in range(4):
        envs, qo, qt = O.random_case(100 + seed)
        H.run_and_compare(envs, qo, qt, 3, 0.99, True, False, rel=1e-5)


def test_every_transition_becomes_exactly_one_sample_except_the_unfinished_tail():
    for n in (1, 3):
        for seed in range(6):
            envs, qo, qt = O.random_case(200 + seed)
            _, counts, _, replay = H.run_pipeline(envs, qo, qt, n, GAMMA)
            transitions = sum(len(ep) for ep in envs[0]) * len(envs)
            pending = sum(len(q) for q in replay.pending)
            assert counts[-1] + pending == transitions and pending <= (n - 1) * len(envs)


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_the_oracle_catches_each_planted_bug(name):
    """Mutation check: every deliberately broken variant must disagree with the oracle on at least one case."""
    impl = MUTANTS[name]()
    caught = False
    for case in CASES:
        for n in (1, 3):
            for double in (True, False):
                try:
                    H.run_and_compare(case["envs"], case["q_online"], case["q_target"], n, GAMMA, double, False, **impl)
                except AssertionError:
                    caught = True
    for seed in range(6):
        envs, qo, qt = O.random_case(300 + seed)
        for n in (1, 3):
            try:
                H.run_and_compare(envs, qo, qt, n, GAMMA, True, False, **impl)
            except AssertionError:
                caught = True
    assert caught, f"planted bug {name!r} was not detected"


def test_unmutated_pipeline_passes_everything_the_mutants_are_tested_with():
    for case in CASES:
        for n in (1, 3):
            H.run_and_compare(case["envs"], case["q_online"], case["q_target"], n, GAMMA, True, False)


def test_train_loop_uses_the_extracted_helpers():
    """The helpers are not dead code: train() must route its targets and its environment stepping through them."""
    import inspect

    src = inspect.getsource(dqn.train)
    assert "td_target(" in src and "collect_step(" in src


def test_evidence_report_runs_and_is_green():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "nstep_oracle_report.py"
    spec = importlib.util.spec_from_file_location("nstep_oracle_report", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = mod.build()
    assert "**overall: PASS**" in text and "NOT DETECTED" not in text and "reviewer: ``" in text  # reviewer stays empty
