# quick_test.py
from feature_matcher_cv import FeatureMatcherOptimizer, save_homographies_json, draw_matches, match_details
import json, cv2

pairs = [("data/A1.png","data/B1.png"), ("data/A2.png","data/B2.png")]

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
    param_grid=grid,
    alpha_rmse=0.12,
    cv_mode="kfold",
    n_splits=4,
    n_jobs=-1,
    successive_halving=False,
    min_inliers_threshold=8,
    warmup_pairs=1,
    time_limit_s=1.2,
    patience_bad_folds=1.5
)

best, report = opt.fit(pairs)
print("[BEST]\n", json.dumps(best, indent=2))
print("[REPORT]\n", json.dumps({k:v for k,v in report.items() if k!='ranking'}, indent=2))

# Guardar homografías
save_homographies_json(pairs, best, "out/homogs_lib.json", alpha_rmse=0.12)

# Visual (primer par)
vis = draw_matches(pairs[0][0], pairs[0][1], {**best, "alpha_rmse": 0.12}, max_draw=80)
cv2.imwrite("out/matches_lib.png", vis)

# Inspección detallada de un par
det = match_details(pairs[0][0], pairs[0][1], best.get("detector","ORB"),
                    best.get("matcher_type","auto"), best.get("ratio_thresh",0.75),
                    best.get("ransac_thresh",3.0), 0.12,
                    **{k:v for k,v in best.items() if k.startswith(("orb_","sift_","akaze_"))})
print("[DETAIL A1-B1] inliers:", det["inliers"], "rmse:", det["rmse"])