import random

import pytest

from backend.src.services.ml.model import MIN_TRAIN_SAMPLES, EngineModel

NAMES = ("a", "b", "c")


def _samples(n, learnable, seed=1):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        a, b = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
        label = int(a > 0) if learnable else rnd.randint(0, 1)
        out.append((float(i), {"a": a, "b": b, "c": 0.0}, label))
    return out


def test_no_model_scores_none(tmp_path):
    m = EngineModel("breakout", NAMES, tmp_path)
    assert m.score({"a": 1}) is None and not m.has_model


def test_refuses_to_train_on_too_few(tmp_path):
    rep = EngineModel("breakout", NAMES, tmp_path).train(_samples(MIN_TRAIN_SAMPLES - 1, True))
    assert not rep["accepted"] and "need" in rep["reason"]


def test_learnable_data_is_accepted_and_scores(tmp_path):
    m = EngineModel("breakout", NAMES, tmp_path)
    rep = m.train(_samples(300, True))
    assert rep["accepted"] and rep["holdout_auc"] > 0.8
    assert m.score({"a": 0.9, "b": 0}) > 0.5 > m.score({"a": -0.9, "b": 0})


def test_noise_is_rejected_by_the_holdout(tmp_path):
    m = EngineModel("breakout", NAMES, tmp_path)
    rep = m.train(_samples(300, False, seed=3))
    assert not rep["accepted"] and not m.has_model


def test_appended_feature_hands_over_to_narrower_model(tmp_path):
    old = EngineModel("reversal", ("a", "b"), tmp_path)
    assert old.train(_samples(300, True))["accepted"]
    new = EngineModel("reversal", ("a", "b", "new_feature"), tmp_path)
    assert new.load() and new.meta["handover"] is True
    assert new.score({"a": 0.9, "b": 0, "new_feature": 5}) > 0.5


def test_models_are_per_engine(tmp_path):
    EngineModel("breakout", NAMES, tmp_path).train(_samples(300, True))
    assert not EngineModel("trend_pa", NAMES, tmp_path).load()


def test_an_accepted_model_reports_what_it_learned_from(tmp_path):
    # Only "a" decides the label, so it must top the importances.
    rep = EngineModel("breakout", NAMES, tmp_path).train(_samples(300, True))
    assert rep["accepted"]
    names = [n for n, _ in rep["top_features"]]
    assert names[0] == "a" and set(names) <= set(NAMES)
    assert sum(v for _, v in rep["top_features"]) == pytest.approx(1.0, abs=0.01)
