"""Resumen de rasgos de arsenal/tunneling por familia (agregados, sin lanzamientos). Uso: python reports/features/make_features_report.py"""
import warnings
from pathlib import Path

from stuffplus.features.arsenal import fit_arsenal
from stuffplus.features.identity import assign_pitch_id
from stuffplus.features.sequence import add_sequence_features
from stuffplus.io import load_raw
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
d = assign_pitch_id(clean(load_raw()))
o = add_sequence_features(fit_arsenal(d).transform(d))
cols = ["velo_diff_vs_fb", "ivb_diff_vs_fb", "hb_diff_vs_fb", "spin_diff_vs_fb", "axis_diff_vs_fb", "pitch_usage_pct",
        "release_dist_vs_fb", "decision_sep_vs_fb", "plate_sep_vs_fb", "tunnel_ratio", "prev_velo_diff", "prev_loc_diff"]
t = o.groupby("pitch_family")[cols].median().round(3)
t["n"] = o.groupby("pitch_family").size()
t["share_same_game_ref"] = o.groupby("pitch_family").fb_ref_same_game.mean().round(3)
t.to_csv(Path(__file__).with_name("arsenal_by_family.csv"))
print(t.T)
