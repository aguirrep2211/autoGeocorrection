# file: feature_matcher_cv.py
# -*- coding: utf-8 -*-
"""
Feature matching (OpenCV) + optimización de hiperparámetros con holdout o k-fold.
Incluye ORB/SIFT/AKAZE, paralelización, early-exit, successive halving,
salida de homografías (JSON) y visualización anotada.

Uso como librería
-----------------
from feature_matcher_cv import FeatureMatcherOptimizer, save_homographies_json, draw_matches, single_match, match_details

pairs = [("A1.png","B1.png"), ("A2.png","B2.png")]
grid = {
    "detector": ["SIFT","AKAZE","ORB"],
    "matcher_type": ["auto","flann"],
    "ratio_thresh": [0.7, 0.75],
    "ransac_thresh": [2.0, 3.0],
    "sift_nfeatures": [0, 2000],
    "akaze_threshold": [0.0008, 0.0012],
    "orb_nfeatures": [1500, 2500],
}
opt = FeatureMatcherOptimizer(
    param_grid=grid, alpha_rmse=0.15,
    cv_mode="kfold", n_splits=5, n_jobs=-1,
    successive_halving=False, min_inliers_threshold=10, warmup_pairs=2
)
best, report = opt.fit(pairs)
save_homographies_json(pairs, best, "/tmp/homogs.json", alpha_rmse=0.15)
img = draw_matches(pairs[0][0], pairs[0][1], {**best, "alpha_rmse": 0.15}, max_draw=80)
import cv2; cv2.imwrite("/tmp/matches.png", img)

CLI
---
python feature_matcher_cv.py \
  --pairs pairs.txt \
  --out-json /tmp/report.json \
  --out-hjson /tmp/homogs.json \
  --out-png /tmp/matches.png \
  --cv-mode kfold --n-splits 5 --n-jobs -1 \
  --alpha 0.15 --successive-halving \
  --min-inliers 10 --warmup-pairs 2 --time-limit-s 2.0

El archivo pairs.txt debe tener por línea:  /ruta/img1 ; /ruta/img2   (o separado por coma)
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from sklearn.model_selection import ParameterGrid, train_test_split, KFold
from joblib import Parallel, delayed


# --------------------------- E/S de imágenes y pares ---------------------------

def _read_gray(path: str) -> np.ndarray:
    """Lee una imagen en escala de grises con soporte de rutas Unicode."""
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {path}")
    return img


def _load_pairs_file(pairs_file: str) -> List[Tuple[str, str]]:
    """Carga pares del archivo (separador ';' o ',')."""
    pairs = []
    with open(pairs_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sep = ";" if ";" in line else ","
            a, b = [x.strip() for x in line.split(sep, 1)]
            if not (os.path.exists(a) and os.path.exists(b)):
                raise FileNotFoundError(f"Pares inválidos o rutas inexistentes: {line}")
            pairs.append((a, b))
    return pairs


# --------------------------- Detectores y matchers ---------------------------

def _create_detector(method: str = "ORB", **kwargs):
    m = method.upper()
    if m == "ORB":
        return cv2.ORB_create(
            nfeatures=kwargs.get("orb_nfeatures", 2000),
            scaleFactor=kwargs.get("orb_scaleFactor", 1.2),
            nlevels=kwargs.get("orb_nlevels", 8),
            edgeThreshold=kwargs.get("orb_edgeThreshold", 31),
            firstLevel=kwargs.get("orb_firstLevel", 0),
            WTA_K=kwargs.get("orb_WTA_K", 2),
            scoreType=kwargs.get("orb_scoreType", cv2.ORB_HARRIS_SCORE),
            patchSize=kwargs.get("orb_patchSize", 31),
            fastThreshold=kwargs.get("orb_fastThreshold", 20),
        )
    elif m == "SIFT":
        # Requiere opencv-contrib-python
        return cv2.SIFT_create(
            nfeatures=kwargs.get("sift_nfeatures", 0),
            nOctaveLayers=kwargs.get("sift_nOctaveLayers", 3),
            contrastThreshold=kwargs.get("sift_contrastThreshold", 0.04),
            edgeThreshold=kwargs.get("sift_edgeThreshold", 10),
            sigma=kwargs.get("sift_sigma", 1.6),
        )
    elif m == "AKAZE":
        # Por defecto produce descriptores binarios (MLDB)
        return cv2.AKAZE_create(
            descriptor_type=kwargs.get("akaze_descriptor_type", cv2.AKAZE_DESCRIPTOR_MLDB),
            descriptor_size=kwargs.get("akaze_descriptor_size", 0),
            descriptor_channels=kwargs.get("akaze_descriptor_channels", 3),
            threshold=kwargs.get("akaze_threshold", 0.001),
            nOctaves=kwargs.get("akaze_nOctaves", 4),
            nOctaveLayers=kwargs.get("akaze_nOctaveLayers", 4),
            diffusivity=kwargs.get("akaze_diffusivity", cv2.KAZE_DIFF_PM_G2),
        )
    else:
        raise ValueError("method debe ser 'ORB','SIFT' o 'AKAZE'")


def _create_matcher(matcher_type: str, desc_dtype: Optional[np.dtype]) -> cv2.DescriptorMatcher:
    """
    matcher_type: {'auto','bf','flann'}
    - 'auto' elige BF/FLANN y norma según dtype (Hamming para binarios, L2 para float).
    """
    def _is_binary(dtype) -> bool:
        return dtype == np.uint8

    m = (matcher_type or "auto").lower()
    if m == "bf" or (m == "auto" and desc_dtype is not None):
        return cv2.BFMatcher(cv2.NORM_HAMMING if _is_binary(desc_dtype) else cv2.NORM_L2, crossCheck=False)

    if m == "flann" or m == "auto":
        if desc_dtype is None:
            # Fallback seguro
            return cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        if _is_binary(desc_dtype):
            # FLANN LSH
            index_params = dict(algorithm=6, table_number=12, key_size=20, multi_probe_level=2)
            search_params = dict(checks=64)
            return cv2.FlannBasedMatcher(index_params, search_params)
        # FLANN KDTree
        index_params = dict(algorithm=1, trees=5)  # FLANN_INDEX_KDTREE
        search_params = dict(checks=64)
        return cv2.FlannBasedMatcher(index_params, search_params)

    raise ValueError("matcher_type debe ser {'auto','bf','flann'}")


# --------------------------- Núcleo: matching y scoring ---------------------------

@dataclass
class MatchResult:
    H: Optional[np.ndarray]
    inliers: int
    rmse: Optional[float]
    total_kp1: int
    total_kp2: int
    good_matches: int
    cost: float
    mask_inliers: Optional[np.ndarray]


def detect_and_describe(img: np.ndarray, detector) -> Tuple[List[cv2.KeyPoint], Optional[np.ndarray]]:
    kps, desc = detector.detectAndCompute(img, None)
    return kps, desc


def knn_ratio_match(d1: np.ndarray,
                    d2: np.ndarray,
                    matcher: cv2.DescriptorMatcher,
                    ratio_thresh: float = 0.75) -> List[cv2.DMatch]:
    if d1 is None or d2 is None or len(d1) == 0 or len(d2) == 0:
        return []
    knn = matcher.knnMatch(d1, d2, k=2)
    good = []
    for pair in knn:
        if len(pair) == 2:
            m, n = pair
            if n.distance == 0:
                continue
            if m.distance / n.distance < ratio_thresh:
                good.append(m)
    return good


def estimate_homography(kp1: Sequence[cv2.KeyPoint],
                        kp2: Sequence[cv2.KeyPoint],
                        matches: Sequence[cv2.DMatch],
                        ransac_thresh: float = 3.0,
                        confidence: float = 0.999) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    if len(matches) < 4:
        return None, None
    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, ransac_thresh, confidence=confidence)
    return H, mask


def reprojection_rmse(kp1: Sequence[cv2.KeyPoint],
                      kp2: Sequence[cv2.KeyPoint],
                      matches: Sequence[cv2.DMatch],
                      H: np.ndarray,
                      mask_inliers: np.ndarray) -> Optional[float]:
    if H is None or mask_inliers is None or mask_inliers.sum() == 0:
        return None
    src_in = np.float32([kp1[m.queryIdx].pt for i, m in enumerate(matches) if mask_inliers[i]]).reshape(-1, 1, 2)
    dst_in = np.float32([kp2[m.trainIdx].pt for i, m in enumerate(matches) if mask_inliers[i]]).reshape(-1, 1, 2)
    proj = cv2.perspectiveTransform(src_in, H)
    err = np.linalg.norm(proj - dst_in, axis=2).ravel()
    if err.size == 0:
        return None
    return float(math.sqrt((err ** 2).mean()))


def match_and_score(img1: np.ndarray,
                    img2: np.ndarray,
                    detector_name: str = "ORB",
                    params: Dict = None,
                    matcher_type: str = "auto",
                    ratio_thresh: float = 0.75,
                    ransac_thresh: float = 3.0,
                    alpha_rmse: float = 0.1) -> MatchResult:
    params = params or {}
    detector = _create_detector(detector_name, **params)
    kp1, d1 = detect_and_describe(img1, detector)
    kp2, d2 = detect_and_describe(img2, detector)

    desc_dtype = None if d1 is None else d1.dtype
    matcher = _create_matcher(matcher_type, desc_dtype)

    good = knn_ratio_match(d1, d2, matcher, ratio_thresh=ratio_thresh)

    H, mask = estimate_homography(kp1, kp2, good, ransac_thresh=ransac_thresh)
    if mask is not None:
        mask_bool = mask.ravel().astype(bool)
        inliers = int(mask_bool.sum())
    else:
        mask_bool = None
        inliers = 0

    rmse = reprojection_rmse(kp1, kp2, good, H, mask_bool) if H is not None and mask_bool is not None else None

    # Coste: minimizar
    penalty_noH = 1000.0
    if H is None or rmse is None:
        cost = penalty_noH - inliers
    else:
        cost = -inliers + alpha_rmse * rmse

    return MatchResult(
        H=H,
        inliers=inliers,
        rmse=rmse,
        total_kp1=len(kp1),
        total_kp2=len(kp2),
        good_matches=len(good),
        cost=float(cost),
        mask_inliers=mask_bool
    )


# --------------------------- API de alto nivel ---------------------------

def single_match(img_path1: str,
                 img_path2: str,
                 detector: str = "ORB",
                 matcher_type: str = "auto",
                 ratio_thresh: float = 0.75,
                 ransac_thresh: float = 3.0,
                 alpha_rmse: float = 0.1,
                 **detector_params) -> Dict:
    img1 = _read_gray(img_path1)
    img2 = _read_gray(img_path2)
    res = match_and_score(
        img1, img2,
        detector_name=detector,
        params=detector_params,
        matcher_type=matcher_type,
        ratio_thresh=ratio_thresh,
        ransac_thresh=ransac_thresh,
        alpha_rmse=alpha_rmse
    )
    return {
        "H": res.H,
        "inliers": res.inliers,
        "rmse": res.rmse,
        "total_keypoints_img1": res.total_kp1,
        "total_keypoints_img2": res.total_kp2,
        "good_matches": res.good_matches,
        "cost": res.cost,
    }


def match_details(img_path1: str,
                  img_path2: str,
                  detector: str = "ORB",
                  matcher_type: str = "auto",
                  ratio_thresh: float = 0.75,
                  ransac_thresh: float = 3.0,
                  alpha_rmse: float = 0.1,
                  **detector_params) -> Dict:
    """
    Devuelve detalles completos del matching:
      - H (3x3) o None
      - rmse, inliers, good_matches, total_kp1, total_kp2, cost
      - correspondencias inliers: points_src (Nx2), points_dst (Nx2)
    """
    img1 = _read_gray(img_path1)
    img2 = _read_gray(img_path2)

    # Calcula score + máscara
    res = match_and_score(
        img1, img2,
        detector_name=detector,
        params={k: v for k, v in detector_params.items() if k.startswith(("orb_","sift_","akaze_"))},
        matcher_type=matcher_type,
        ratio_thresh=ratio_thresh,
        ransac_thresh=ransac_thresh,
        alpha_rmse=alpha_rmse
    )

    # Recompute KPs + good para extraer puntos inlier
    detector_obj = _create_detector(detector, **{k: v for k, v in detector_params.items()
                                                 if k.startswith(("orb_","sift_","akaze_"))})
    kp1, d1 = detect_and_describe(img1, detector_obj)
    kp2, d2 = detect_and_describe(img2, detector_obj)
    desc_dtype = None if d1 is None else d1.dtype
    matcher = _create_matcher(matcher_type, desc_dtype)
    good = knn_ratio_match(d1, d2, matcher, ratio_thresh=ratio_thresh)

    points_src, points_dst = [], []
    if res.mask_inliers is not None and len(good) > 0:
        for i, m in enumerate(good):
            if res.mask_inliers[i]:
                x, y = kp1[m.queryIdx].pt
                xp, yp = kp2[m.trainIdx].pt
                points_src.append([float(x), float(y)])
                points_dst.append([float(xp), float(yp)])

    H_list = None
    if res.H is not None:
        H_list = [[float(res.H[r, c]) for c in range(3)] for r in range(3)]

    return {
        "img1": img_path1, "img2": img_path2,
        "detector": detector, "matcher_type": matcher_type,
        "ratio_thresh": ratio_thresh, "ransac_thresh": ransac_thresh, "alpha_rmse": alpha_rmse,
        "H": H_list,
        "rmse": res.rmse,
        "inliers": res.inliers,
        "good_matches": res.good_matches,
        "total_keypoints_img1": res.total_kp1,
        "total_keypoints_img2": res.total_kp2,
        "cost": res.cost,
        "points_src": points_src,  # Nx2
        "points_dst": points_dst,  # Nx2
    }


def save_homographies_json(pairs: Sequence[Tuple[str, str]],
                           best_params: Dict,
                           out_json_path: str,
                           alpha_rmse: float = 0.1) -> str:
    """
    Calcula y guarda en JSON la homografía y correspondencias inlier para cada par.
    Devuelve la ruta al JSON.
    """
    det = best_params.get("detector", "ORB")
    matcher_type = best_params.get("matcher_type", "auto")
    ratio = best_params.get("ratio_thresh", 0.75)
    ransac = best_params.get("ransac_thresh", 3.0)
    det_params = {k: v for k, v in best_params.items()
                  if k.startswith(("orb_","sift_","akaze_"))}

    payload = {
        "params": {"detector": det, "matcher_type": matcher_type,
                   "ratio_thresh": ratio, "ransac_thresh": ransac,
                   **det_params, "alpha_rmse": alpha_rmse},
        "pairs": []
    }

    for a, b in pairs:
        payload["pairs"].append(
            match_details(a, b, det, matcher_type, ratio, ransac, alpha_rmse, **det_params)
        )

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_json_path


def draw_matches(img_path1: str,
                 img_path2: str,
                 params: Dict,
                 max_draw: int = 60,
                 annotate: bool = True) -> np.ndarray:
    """
    Devuelve imagen con líneas de correspondencia (inliers resaltados si hay máscara).
    Anota RMSE, #inliers, #good, detector, etc.
    """
    img1 = _read_gray(img_path1)
    img2 = _read_gray(img_path2)

    detector = params.get("detector", "ORB")
    matcher_type = params.get("matcher_type", "auto")
    ratio_thresh = params.get("ratio_thresh", 0.75)
    ransac_thresh = params.get("ransac_thresh", 3.0)
    alpha_rmse = params.get("alpha_rmse", 0.1)

    det_params = {k: v for k, v in params.items()
                  if k.startswith(("orb_","sift_","akaze_"))}

    # Obtener máscara de inliers y métricas
    res = match_and_score(
        img1, img2,
        detector_name=detector, params=det_params,
        matcher_type=matcher_type, ratio_thresh=ratio_thresh,
        ransac_thresh=ransac_thresh, alpha_rmse=alpha_rmse
    )

    # Recalcular KPs y matches para dibujar
    detector_obj = _create_detector(detector, **det_params)
    kp1, d1 = detect_and_describe(img1, detector_obj)
    kp2, d2 = detect_and_describe(img2, detector_obj)
    desc_dtype = None if d1 is None else d1.dtype
    matcher = _create_matcher(matcher_type, desc_dtype)
    good = knn_ratio_match(d1, d2, matcher, ratio_thresh=ratio_thresh)

    draw_list = good[:max_draw]
    mask_draw = None
    if res.mask_inliers is not None:
        mask_draw = res.mask_inliers[:len(draw_list)].astype(np.uint8).tolist()

    vis = cv2.drawMatches(
        img1, kp1, img2, kp2, draw_list, None,
        matchesMask=mask_draw,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    )

    if annotate:
        h, w = vis.shape[:2]
        pad = 10
        overlay = vis.copy()
        cv2.rectangle(overlay, (pad, pad), (min(w-1, 520), pad+110), (0, 0, 0), -1)
        vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)

        tx = pad + 8
        ty = pad + 22

        def put(s):
            nonlocal ty
            cv2.putText(vis, s, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            ty += 24

        put(f"Detector: {detector}  |  Matcher: {matcher_type}")
        put(f"Good: {res.good_matches}  |  Inliers: {res.inliers}")
        put(f"RMSE: {None if res.rmse is None else round(res.rmse, 3)}  |  Cost: {round(res.cost, 3)}")
        put(f"Ratio: {ratio_thresh}  |  RANSAC: {ransac_thresh}")

    return vis


# --------------------------- Optimizador con early-exit ---------------------------

class FeatureMatcherOptimizer:
    """
    Optimización con holdout o k-fold, paralelización y early-exit.

    Early-exit / pruning:
      - min_inliers_threshold: si tras 'warmup_pairs' la media de inliers < umbral, aborta combinación.
      - time_limit_s: límite de tiempo por combinación (soft-stop).
      - successive_halving: evalúa fracción creciente de pares (rung=1/eta, 1/2, 1) conservando el 1/eta mejores.
      - patience_bad_folds: en k-fold, si el coste acumulado supera X * mejor_coste, se corta.

    Param grid (claves típicas):
      - detector: ['SIFT','AKAZE','ORB']
      - matcher_type: ['auto','bf','flann']
      - ratio_thresh: [0.7,0.75]
      - ransac_thresh: [2.0,3.0]
      - Específicos:
        ORB:   orb_nfeatures, orb_scaleFactor, orb_nlevels, ...
        SIFT:  sift_nfeatures, sift_nOctaveLayers, sift_contrastThreshold, ...
        AKAZE: akaze_threshold, akaze_nOctaves, akaze_descriptor_type, ...
    """

    def __init__(self,
                 param_grid: Dict[str, List],
                 alpha_rmse: float = 0.1,
                 test_size: float = 0.25,
                 random_state: int = 42,
                 cv_mode: str = "holdout",
                 n_splits: int = 5,
                 n_jobs: int = -1,
                 # Early-exit:
                 min_inliers_threshold: Optional[int] = None,
                 warmup_pairs: int = 2,
                 time_limit_s: Optional[float] = None,
                 successive_halving: bool = False,
                 halving_eta: int = 3,
                 patience_bad_folds: Optional[float] = None):
        self.param_grid = list(ParameterGrid(param_grid))
        if not self.param_grid:
            raise ValueError("param_grid vacío.")

        self.alpha_rmse = alpha_rmse
        self.test_size = test_size
        self.random_state = random_state
        self.cv_mode = cv_mode
        self.n_splits = n_splits
        self.n_jobs = n_jobs

        # Early-exit
        self.min_inliers_threshold = min_inliers_threshold
        self.warmup_pairs = max(1, warmup_pairs)
        self.time_limit_s = time_limit_s
        self.successive_halving = successive_halving
        self.halving_eta = max(2, halving_eta)
        self.patience_bad_folds = patience_bad_folds

        self.best_params_: Optional[Dict] = None
        self.summary_: Optional[Dict] = None

    @staticmethod
    def _eval_pair(pair: Tuple[str, str], params: Dict, alpha_rmse: float) -> Tuple[float, int]:
        p1, p2 = pair
        img1, img2 = _read_gray(p1), _read_gray(p2)

        detector = params.get("detector", "ORB")
        matcher_type = params.get("matcher_type", "auto")
        ratio_thresh = params.get("ratio_thresh", 0.75)
        ransac_thresh = params.get("ransac_thresh", 3.0)

        det_params = {k: v for k, v in params.items() if k.startswith(("orb_", "sift_", "akaze_"))}

        res = match_and_score(
            img1, img2,
            detector_name=detector,
            params=det_params,
            matcher_type=matcher_type,
            ratio_thresh=ratio_thresh,
            ransac_thresh=ransac_thresh,
            alpha_rmse=alpha_rmse
        )
        return res.cost, res.inliers

    def _mean_cost_with_early_exit(self, pairs_subset, params):
        """
        Compute mean cost over a subset of pairs with optional early exit based on:
        - time limit
        - minimum inliers threshold after warmup
        Returns a float cost (lower is better), or +inf on hard failure.
        """
        start = time.time()

        # Empty subset guard
        if not pairs_subset:
            return float("inf")

        inliers_hist = []
        costs = []

        # Clamp warmup to the actual subset size
        eff_warmup = int(min(max(int(self.warmup_pairs), 0), len(pairs_subset)))

        for i, pair in enumerate(pairs_subset, 1):
            # --- time limit early exit ---
            if self.time_limit_s is not None and (time.time() - start) > float(self.time_limit_s):
                # If we have at least one cost, return its mean; else +inf
                return float(np.mean(costs)) if costs else float("inf")

            # Do the actual matching/eval for this pair
            try:
                # use the existing _eval_pair helper (staticmethod) and pass alpha_rmse
                cost_i, inliers_i = self._eval_pair(pair, params, self.alpha_rmse)
            except Exception:
                # hard failure for this pair -> treat as worst case
                cost_i, inliers_i = float("inf"), 0

            costs.append(cost_i)
            inliers_hist.append(inliers_i)

            # --- min inliers early exit (after warmup) ---
            if self.min_inliers_threshold is not None and i >= eff_warmup and eff_warmup > 0:
                # mean inliers over the pairs seen so far
                mean_inl = float(np.mean(inliers_hist))
                if mean_inl < float(self.min_inliers_threshold):
                    return float("inf")

        # Normal completion: return mean cost
        return float(np.mean(costs)) if costs else float("inf")


    def _successive_halving_search(self, pairs: List[Tuple[str, str]]) -> Dict:
        # rungs: 1/eta del conjunto, luego 1/2, y finalmente full
        rungs = []
        # Primer rung: 1/eta del total (al menos 1)
        rungs.append(max(1, len(pairs) // self.halving_eta))
        # Segundo rung: mitad
        rungs.append(max(1, len(pairs) // 2))
        # Final: todos
        rungs.append(len(pairs))

        candidates = list(self.param_grid)
        ranking_info = []
        n_samples = len(pairs)
        if self.cv_mode == "kfold":
            if self.n_splits > n_samples:
                print(f"[warn] Requested n_splits={self.n_splits} > n_samples={n_samples}. "
                    f"Clamping to {n_samples}.")
                self.n_splits = n_samples
            if self.n_splits < 2:
                # fallback to holdout when too few samples for KFold
                print("[warn] Not enough samples for KFold. Falling back to holdout CV.")
                self.cv_mode = "holdout"
                self.val_frac = 0.5  # or whatever your default is

        for r, n_pairs in enumerate(rungs, 1):
            subset = pairs[:n_pairs]
            scored = []
            for p in candidates:
                mean_c = self._mean_cost_with_early_exit(subset, p)
                scored.append((mean_c, p))
            scored.sort(key=lambda x: x[0])
            keep = max(1, len(scored) // self.halving_eta) if r < len(rungs) else len(scored)
            candidates = [p for _, p in scored[:keep]]
            ranking_info.append({"rung": r, "n_pairs": n_pairs,
                                 "keep": keep, "scores": [{"mean_cost": c, "params": par} for c, par in scored]})

        best_params = candidates[0]
        best_cost = self._mean_cost_with_early_exit(pairs, best_params)
        return {"best_params": best_params, "best_cost": best_cost, "rungs": ranking_info}

    def fit(self, pairs: Sequence[Tuple[str, str]]) -> Tuple[Dict, Dict]:
        pairs = list(pairs)
        if len(pairs) < 2:
            raise ValueError("Se requieren al menos 2 pares.")
        report = {"grid_size": len(self.param_grid)}

        if self.cv_mode == "kfold":
            n_samples = len(pairs)
            if self.cv_mode == "kfold":
                if self.n_splits > n_samples:
                    print(f"[warn] Requested n_splits={self.n_splits} > n_samples={n_samples}. "
                        f"Clamping to {n_samples}.")
                    self.n_splits = n_samples
                if self.n_splits < 2:
                    print("[warn] Not enough samples for KFold. Falling back to holdout CV.")
                    self.cv_mode = "holdout"    


            kf = KFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_state)
            best_params, best_score = None, float("inf")
            all_scores = []

            for params in self.param_grid:
                fold_costs = []
                for fold_idx, (tr_idx, va_idx) in enumerate(kf.split(pairs), 1):
                    val_pairs = [pairs[i] for i in va_idx]
                    c = self._mean_cost_with_early_exit(val_pairs, params)
                    fold_costs.append(c)

                    # Paciencia: si ya es mucho peor que el mejor, corto
                    if self.patience_bad_folds is not None and best_score < float("inf"):
                        current_mean = float(np.mean(fold_costs))
                        if current_mean > self.patience_bad_folds * best_score:
                            break

                mean_c, std_c = float(np.mean(fold_costs)), float(np.std(fold_costs))
                all_scores.append({"params": params, "val_mean_cost": mean_c, "val_std_cost": std_c})
                if mean_c < best_score:
                    best_score, best_params = mean_c, dict(params)

            self.best_params_ = best_params
            self.summary_ = {
                **report,
                "cv_mode": "kfold",
                "n_splits": self.n_splits,
                "best_cv_mean_cost": best_score,
                "ranking": sorted(all_scores, key=lambda x: x["val_mean_cost"]),
            }
            return best_params, self.summary_

        # HOLDOUT
        train, test = train_test_split(pairs, test_size=self.test_size,
                                       random_state=self.random_state, shuffle=True)

        if self.successive_halving:
            sh = self._successive_halving_search(train)
            best_params, best_train_cost = sh["best_params"], sh["best_cost"]
            test_costs = [self._mean_cost_with_early_exit([t], best_params) for t in test]
            self.best_params_ = best_params
            self.summary_ = {
                **report,
                "cv_mode": "holdout+successive_halving",
                "n_train": len(train), "n_test": len(test),
                "best_train_cost": best_train_cost,
                "test_mean_cost": float(np.mean(test_costs)) if test_costs else None,
                "rungs": sh["rungs"],
            }
            return best_params, self.summary_

        # Holdout plano
        best_cost, best_params, train_costs = float("inf"), None, []
        for params in self.param_grid:
            mean_c = self._mean_cost_with_early_exit(train, params)
            train_costs.append((params, mean_c))
            if mean_c < best_cost:
                best_cost, best_params = mean_c, dict(params)

        test_costs = [self._mean_cost_with_early_exit([t], best_params) for t in test]
        self.best_params_ = best_params
        self.summary_ = {
            **report,
            "cv_mode": "holdout",
            "n_train": len(train), "n_test": len(test),
            "best_train_cost": best_cost,
            "test_mean_cost": float(np.mean(test_costs)) if test_costs else None,
            "test_std_cost": float(np.std(test_costs)) if test_costs else None,
            "train_costs": [{"params": p, "mean_cost": c} for (p, c) in sorted(train_costs, key=lambda x: x[1])],
        }
        return best_params, self.summary_


# --------------------------- CLI ---------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimización de feature matching con OpenCV + scikit-learn.")
    parser.add_argument("--pairs", type=str, required=True,
                        help="Archivo con pares de imágenes (línea: 'img1;img2' o 'img1,img2').")
    parser.add_argument("--grid", type=str, default="{}",
                        help='JSON con param_grid. Si se omite, se usa un grid por defecto.')
    parser.add_argument("--alpha", type=float, default=0.1, help="Peso del RMSE en el coste (menor=prioriza inliers).")
    parser.add_argument("--cv-mode", type=str, default="holdout", choices=["holdout", "kfold"])
    parser.add_argument("--n-splits", type=int, default=5, help="Folds para k-fold.")
    parser.add_argument("--test-size", type=float, default=0.25, help="Proporción de test (holdout).")
    parser.add_argument("--n-jobs", type=int, default=-1, help="Paralelización sobre pares (no-aplica en early-exit).")

    # Early-exit / pruning
    parser.add_argument("--successive-halving", action="store_true", help="Activa successive halving (holdout).")
    parser.add_argument("--halving-eta", type=int, default=3, help="Factor de reducción de SH (>=2).")
    parser.add_argument("--min-inliers", type=int, default=None, help="Umbral medio de inliers tras warmup.")
    parser.add_argument("--warmup-pairs", type=int, default=2, help="# pares antes de aplicar min-inliers.")
    parser.add_argument("--time-limit-s", type=float, default=None, help="Límite de tiempo por combinación.")
    parser.add_argument("--patience-bad-folds", type=float, default=None,
                        help="En k-fold, corta si coste acumulado > factor * mejor_coste.")

    # Salidas
    parser.add_argument("--out-json", type=str, required=True, help="Ruta del informe principal (JSON).")
    parser.add_argument("--out-hjson", type=str, required=False, default=None,
                        help="Ruta del JSON con homografías por par.")
    parser.add_argument("--out-png", type=str, required=False, default=None,
                        help="Ruta del PNG con matches del primer par.")
    parser.add_argument("--draw-max", type=int, default=60, help="Máximo nº de matches dibujados en el PNG.")

    args = parser.parse_args()

    # Cargar pares y grid
    pairs = _load_pairs_file(args.pairs)
    grid = json.loads(args.grid) if args.grid.strip() else {
        "detector": ["SIFT", "AKAZE", "ORB"],
        "matcher_type": ["auto", "flann"],
        "ratio_thresh": [0.7, 0.75],
        "ransac_thresh": [2.0, 3.0],
        # SIFT
        "sift_nfeatures": [0, 2000],
        # AKAZE
        "akaze_threshold": [0.0008, 0.0012],
        "akaze_nOctaves": [4, 6],
        # ORB
        "orb_nfeatures": [1500, 2500],
        "orb_scaleFactor": [1.2, 1.4],
        "orb_nlevels": [8, 12],
    }

    # Ejecutar optimización
    opt = FeatureMatcherOptimizer(
        param_grid=grid,
        alpha_rmse=args.alpha,
        test_size=args.test_size,
        random_state=42,
        cv_mode=args.cv_mode,
        n_splits=args.n_splits,
        n_jobs=args.n_jobs,
        successive_halving=args.successive_halving,
        halving_eta=args.halving_eta,
        min_inliers_threshold=args.min_inliers,
        warmup_pairs=args.warmup_pairs,
        time_limit_s=args.time_limit_s,
        patience_bad_folds=args.patience_bad_folds
    )
    best, report = opt.fit(pairs)

    # Guardar informe principal
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump({"best": best, "report": report}, f, ensure_ascii=False, indent=2)

    # Guardar homografías por par si se ha pedido
    if args.out_hjson:
        try:
            save_homographies_json(pairs, {**best}, args.out_hjson, alpha_rmse=args.alpha)
        except Exception as e:
            print(f"[WARN] No se pudo escribir OUT_HJSON: {e}")

    # Guardar PNG de matches del primer par si se ha pedido
    if args.out_png and pairs:
        try:
            vis = draw_matches(pairs[0][0], pairs[0][1], {**best, "alpha_rmse": args.alpha}, max_draw=args.draw_max)
            ok = cv2.imwrite(args.out_png, vis)
            print(f"[INFO] PNG de matches guardado en: {args.out_png} (ok={ok})")
        except Exception as e:
            print(f"[WARN] No se pudo guardar OUT_PNG: {e}")

    # Mensaje final
    print(json.dumps({"best": best, "report": report}, ensure_ascii=False))
