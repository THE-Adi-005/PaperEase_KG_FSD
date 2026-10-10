"""Generate ablation YAML configuration files in configs/."""

import copy
from pathlib import Path

# Ensure backend directory is in sys.path
import sys
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schema_profiles import PROFILES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"

BASE_CONFIG = {
    "config_id": "cfg_base",
    "prompt_profile": "R7",
    "runs": 3,
    "vote_fraction": 0.5,
    "cap": 0,
    "enforce_signatures": False,
    "allow_dynamic": False,
    "drop_generic": False,
    "relation_subset": None,
    "include_tables": True,
    "enable_same_as": True,
    "same_as_threshold": 0.85,
    "trunc": 3000,
    "temperature": 0.6,
    "papers": "all",
}


def dump_yaml(data: dict, out_path: Path, comment: str | None = None) -> None:
    """Format clean YAML with optional header comment."""
    lines = []
    if comment:
        for c_line in comment.strip().splitlines():
            lines.append(f"# {c_line}")
    for k, v in data.items():
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        elif isinstance(v, str):
            lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_configs() -> list[str]:
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    created = []

    # 1. Base
    c_base = copy.deepcopy(BASE_CONFIG)
    c_base["config_id"] = "cfg_base"
    dump_yaml(c_base, CONFIGS_DIR / "cfg_base.yaml")
    created.append("cfg_base")

    # 2. Schema
    # cfg_r3
    c_r3 = copy.deepcopy(BASE_CONFIG)
    c_r3["config_id"] = "cfg_r3"
    c_r3["prompt_profile"] = "R3"
    dump_yaml(c_r3, CONFIGS_DIR / "cfg_r3.yaml")
    created.append("cfg_r3")

    # cfg_r5 (post-hoc)
    r5_relations = PROFILES["R5"].llm_relations
    c_r5 = copy.deepcopy(BASE_CONFIG)
    c_r5["config_id"] = "cfg_r5"
    c_r5["prompt_profile"] = "R7"
    c_r5["relation_subset"] = r5_relations
    dump_yaml(c_r5, CONFIGS_DIR / "cfg_r5.yaml", comment="post-hoc: prompt R7 with relation_subset = R5 relations")
    created.append("cfg_r5")

    # cfg_r10
    c_r10 = copy.deepcopy(BASE_CONFIG)
    c_r10["config_id"] = "cfg_r10"
    c_r10["prompt_profile"] = "R10"
    dump_yaml(c_r10, CONFIGS_DIR / "cfg_r10.yaml")
    created.append("cfg_r10")

    # 3. Votes
    # cfg_v_run1
    c_v1 = copy.deepcopy(BASE_CONFIG)
    c_v1["config_id"] = "cfg_v_run1"
    c_v1["runs"] = 1
    dump_yaml(c_v1, CONFIGS_DIR / "cfg_v_run1.yaml")
    created.append("cfg_v_run1")

    # cfg_v_union
    c_vu = copy.deepcopy(BASE_CONFIG)
    c_vu["config_id"] = "cfg_v_union"
    c_vu["vote_fraction"] = 0.0
    dump_yaml(c_vu, CONFIGS_DIR / "cfg_v_union.yaml")
    created.append("cfg_v_union")

    # cfg_v_unan
    c_va = copy.deepcopy(BASE_CONFIG)
    c_va["config_id"] = "cfg_v_unan"
    c_va["vote_fraction"] = 1.0
    dump_yaml(c_va, CONFIGS_DIR / "cfg_v_unan.yaml")
    created.append("cfg_v_unan")

    # 4. Cap
    for cap_val, name in [(5, "cfg_k5"), (10, "cfg_k10"), (20, "cfg_k20")]:
        c_k = copy.deepcopy(BASE_CONFIG)
        c_k["config_id"] = name
        c_k["cap"] = cap_val
        dump_yaml(c_k, CONFIGS_DIR / f"{name}.yaml")
        created.append(name)

    # 5. Constraints
    c_sig = copy.deepcopy(BASE_CONFIG)
    c_sig["config_id"] = "cfg_sig_on"
    c_sig["enforce_signatures"] = True
    dump_yaml(c_sig, CONFIGS_DIR / "cfg_sig_on.yaml")
    created.append("cfg_sig_on")

    c_dyn = copy.deepcopy(BASE_CONFIG)
    c_dyn["config_id"] = "cfg_dyn_on"
    c_dyn["allow_dynamic"] = True
    dump_yaml(c_dyn, CONFIGS_DIR / "cfg_dyn_on.yaml")
    created.append("cfg_dyn_on")

    # 6. Tables
    c_notables = copy.deepcopy(BASE_CONFIG)
    c_notables["config_id"] = "cfg_no_tables"
    c_notables["include_tables"] = False
    dump_yaml(c_notables, CONFIGS_DIR / "cfg_no_tables.yaml")
    created.append("cfg_no_tables")

    # 7. Same_as
    c_sa_off = copy.deepcopy(BASE_CONFIG)
    c_sa_off["config_id"] = "cfg_sa_off"
    c_sa_off["enable_same_as"] = False
    dump_yaml(c_sa_off, CONFIGS_DIR / "cfg_sa_off.yaml")
    created.append("cfg_sa_off")

    c_sa_070 = copy.deepcopy(BASE_CONFIG)
    c_sa_070["config_id"] = "cfg_sa_070"
    c_sa_070["same_as_threshold"] = 0.70
    dump_yaml(c_sa_070, CONFIGS_DIR / "cfg_sa_070.yaml")
    created.append("cfg_sa_070")

    c_sa_090 = copy.deepcopy(BASE_CONFIG)
    c_sa_090["config_id"] = "cfg_sa_090"
    c_sa_090["same_as_threshold"] = 0.90
    dump_yaml(c_sa_090, CONFIGS_DIR / "cfg_sa_090.yaml")
    created.append("cfg_sa_090")

    # 8. Generic filter
    c_nogeneric = copy.deepcopy(BASE_CONFIG)
    c_nogeneric["config_id"] = "cfg_nogeneric"
    c_nogeneric["drop_generic"] = True
    dump_yaml(c_nogeneric, CONFIGS_DIR / "cfg_nogeneric.yaml")
    created.append("cfg_nogeneric")

    return created


if __name__ == "__main__":
    configs = generate_configs()
    print(f"Generated {len(configs)} configuration YAML files in {CONFIGS_DIR}:")
    for name in configs:
        print(f"  - {name}.yaml")
