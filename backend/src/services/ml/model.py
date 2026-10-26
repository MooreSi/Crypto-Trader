"""One engine's model: train, validate, save, load, score.

Each engine owns an `EngineModel` with its own feature list and its own
files under `MODELS_DIR/<engine>/`. Nothing is shared between engines but
this code: no file, no row, no label. (FOREX Trader's rule, kept: total
isolation between engines.)

**What it predicts:** the probability that a signal makes money net of fees
under the live exit plan (TP ladder, breakeven move, taker fees, from the
real fill when it traded). The engine's tracker writes that label for every
signal, executed or not; labels an older rule wrote are never trained on.

**Validation before use.** A retrain fits on the oldest 80% of labelled
signals and scores the newest 20%. The model is kept only if its holdout AUC
beats a coin flip with 95% one-sided confidence: AUC > 0.5 + 1.645 x SE,
where SE is the AUC's standard error under "no skill" (Mann-Whitney:
sqrt((n_pos + n_neg + 1) / (12 n_pos n_neg))). Otherwise the previous model
stays, or none. A model that cannot beat a coin flip on data it never saw
must not gate real orders.

A fixed margin was tried first (AUC >= 0.53) and the suite's noise test
caught it: on a 60-signal holdout, pure noise clears 0.53 roughly a third of
the time.

**No model is not a veto.** `score()` returns None with no model, and the ML
gate then passes unless `ml_require_model` is on. That is FOREX Trader's
fail-open behaviour, kept deliberately so a fresh install can trade, and
written here so nobody mistakes it for a filter that is running.

**Version handover.** The file name carries the feature count. When features
are appended, the newest model on disk is narrower; it is loaded and scores
the leading features it was trained on (valid because features are
append-only) until the next successful retrain replaces it.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Optional, Sequence

from backend.src.services.ml.features import to_row
from backend.src.utils import clock

log = logging.getLogger(__name__)

MIN_TRAIN_SAMPLES = 60
HOLDOUT_FRACTION = 0.2
#: One-sided 95% z-score for the holdout AUC test.
AUC_Z = 1.645
#: How many of the model's most important features the train report lists.
TOP_FEATURES = 8


def _auc(y: Sequence[int], p: Sequence[float]) -> float:
    pos = [s for s, t in zip(p, y) if t == 1]
    neg = [s for s, t in zip(p, y) if t == 0]
    if not pos or not neg:
        return 0.5
    wins = sum((1.0 if a > b else 0.5 if a == b else 0.0) for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


def auc_threshold(y: Sequence[int]) -> float:
    """The AUC a model must beat to be better than chance at 95% (one-sided)."""
    n_pos = sum(1 for t in y if t == 1)
    n_neg = len(y) - n_pos
    if not n_pos or not n_neg:
        return 1.0
    se = ((n_pos + n_neg + 1) / (12.0 * n_pos * n_neg)) ** 0.5
    return 0.5 + AUC_Z * se


class EngineModel:
    def __init__(self, engine: str, feature_names: Sequence[str], models_dir: Path) -> None:
        self.engine = engine
        self.names = tuple(feature_names)
        self.dir = Path(models_dir) / engine
        self._lock = threading.Lock()
        self._model = None
        self._width = 0
        self.meta: dict = {}

    # ── files ────────────────────────────────────────────────────────────────
    def _path(self, width: int) -> Path:
        return self.dir / f"{self.engine}_model_v{width}.joblib"

    def _versions(self) -> list[int]:
        if not self.dir.exists():
            return []
        found = []
        for p in self.dir.glob(f"{self.engine}_model_v*.joblib"):
            m = re.search(r"_v(\d+)\.joblib$", p.name)
            if m and int(m.group(1)) <= len(self.names):
                found.append(int(m.group(1)))
        return sorted(found)

    def load(self) -> bool:
        import joblib
        versions = self._versions()
        if not versions:
            return False
        width = versions[-1]
        try:
            model = joblib.load(self._path(width))
            meta_path = self._path(width).with_suffix(".json")
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        except Exception as exc:
            log.warning("[ML:%s] could not load model v%d: %s", self.engine, width, exc)
            return False
        with self._lock:
            self._model, self._width, self.meta = model, width, meta
            self.meta["handover"] = width < len(self.names)
        return True

    @property
    def has_model(self) -> bool:
        return self._model is not None

    # ── use ──────────────────────────────────────────────────────────────────
    def score(self, features: dict) -> Optional[float]:
        with self._lock:
            model, width = self._model, self._width
        if model is None:
            return None
        row = to_row(features, self.names)[:width]
        try:
            return float(model.predict_proba([row])[0][1])
        except Exception as exc:
            log.warning("[ML:%s] scoring failed: %s", self.engine, exc)
            return None

    # ── training ─────────────────────────────────────────────────────────────
    def train(self, samples: list[tuple[float, dict, int]]) -> dict:
        """Fit on (created_at, features, label) samples, oldest first. Returns a report."""
        from sklearn.ensemble import GradientBoostingClassifier
        import joblib

        samples = sorted(samples, key=lambda s: s[0])
        n = len(samples)
        report = {"engine": self.engine, "samples": n, "accepted": False, "at": clock.now()}
        if n < MIN_TRAIN_SAMPLES:
            report["reason"] = f"{n} labelled signals, need {MIN_TRAIN_SAMPLES}"
            return report
        X = [to_row(f, self.names) for _, f, _ in samples]
        y = [int(lbl) for _, _, lbl in samples]
        if len(set(y)) < 2:
            report["reason"] = "every label is the same"
            return report
        cut = int(n * (1 - HOLDOUT_FRACTION))
        if len(set(y[:cut])) < 2 or len(set(y[cut:])) < 2:
            report["reason"] = "train or holdout has one class only"
            return report
        probe = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.05,
                                           subsample=0.8, random_state=7)
        probe.fit(X[:cut], y[:cut])
        auc = _auc(y[cut:], [p[1] for p in probe.predict_proba(X[cut:])])
        need = auc_threshold(y[cut:])
        report.update({"holdout_auc": round(auc, 4), "auc_needed": round(need, 4),
                       "base_rate": round(sum(y) / n, 4)})
        if auc <= need:
            report["reason"] = f"holdout AUC {auc:.3f} is not better than chance (needs > {need:.3f})"
            return report
        final = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.05,
                                           subsample=0.8, random_state=7)
        final.fit(X, y)
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self._path(len(self.names))
        joblib.dump(final, path)
        report["accepted"] = True
        ranked = sorted(zip(self.names, final.feature_importances_), key=lambda x: -x[1])
        report["top_features"] = [[n, round(float(v), 4)] for n, v in ranked[:TOP_FEATURES]]
        path.with_suffix(".json").write_text(json.dumps(report))
        with self._lock:
            self._model, self._width, self.meta = final, len(self.names), dict(report)
            self.meta["handover"] = False
        log.info("[ML:%s] retrained on %d signals, holdout AUC %.3f", self.engine, n, auc)
        return report
