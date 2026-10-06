"""Write FROZEN_PROTOCOL.{json,md} and record the commit hash. Nothing confirmatory runs before this."""
import json, subprocess, sys, datetime
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import ROOT

RES = ROOT / "results"


def main():
    sel = json.loads((RES / "pilot_selection.json").read_text())
    frames = json.loads((RES / "frames.json").read_text())
    power = json.loads((RES / "power.json").read_text()) if (RES / "power.json").exists() else {}
    man = json.loads((RES / "manifest.json").read_text())
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                         cwd=ROOT).stdout.strip()

    op = sel["operating_point"]
    proto = {
        "frozen_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": sha,
        "compactor": "qwen.qwen3-235b-a22b-2507-v1:0",
        "second_family": "meta.llama3-3-70b-instruct-v1:0",
        "small_model": "local:qwen3-8b",
        "judges": ["openai.gpt-oss-120b-1:0", "google.gemma-3-27b-it"],
        "B": op["B"], "T": op["T"], "K": 20,
        "checkpoints": [0, 1, 2, 3, 5, 7, 10, 15, 20],
        "primary_endpoint_k": 10,
        "n_seeds": power.get("chosen", {}).get("n_seeds", 3),
        "operators": ["O1", "O2", "O3", "O4", "O5", "O6", "O6-random", "O6-low", "O7"],
        "slots": sel["O3"]["slots"],
        "O3_label": sel["O3"]["label"],
        "O3_within_tolerance": sel["O3"]["within_tolerance"],
        "W1_stored_words": sel["W1_stored_words"],
        "adequacy": sel["adequacy"],
        "eshift": {
            "n_eligible_families": frames["n_eligible"],
            "eligible_fraction_r": frames["eligible_fraction_r"],
            "min_shift_logodds": frames["min_shift"],
            "n_seeds": power.get("chosen", {}).get("n_seeds", 3),
            "operative_sesoi_pp": power.get("operative_sesoi", 8.0),
            "selection_half": "A (worlds 0-1)", "estimation_half": "B (worlds 2-3)",
        },
        "analysis": {
            "primary_estimator": "family-fixed-effects linear probability model of RETAINED at k=10 "
                                 "on within-family-centred Bradley-Terry surprise x operator, with "
                                 "token-length and digit-format nuisance covariates",
            "main_chain_inference": "two-way crossed cluster bootstrap over families and chain x seed "
                                    "blocks, blocks carrying all paired operators",
            "eshift_inference": "family bootstrap with arm-paired seed blocks resampled within family "
                                "(trajectories are nested within families there)",
            "gatekeeping_order": ["C1 E-SHIFT arm effect", "C2 natural-prior dose response",
                                  "C3 O1xO3 interaction + O3 equivalence"],
            "C1_decision_rule": ["POSITIVE_SUPPORT", "POSITIVE_BELOW_SESOI", "BOUNDARY_EVIDENCE",
                                 "INCONCLUSIVE"],
            "O3_equivalence_margin_pp": 5.0,
            "C1_primary_population": "eligible-only (Half-A screen); ITT reported as sensitivity; "
                                     "C1 declared inconclusive if they disagree in direction",
        },
        "manifest": {"n_conf_chains": man["n_conf_chains"],
                     "chain_sizes": man["confirmatory_manifest"]["chain_sizes"],
                     "max_mean_surprise_gap": man["confirmatory_manifest"]["max_mean_surprise_gap"],
                     "balance_basis": man["confirmatory_manifest"]["balance_basis"]},
    }
    (RES / "FROZEN_PROTOCOL.json").write_text(json.dumps(proto, indent=1))

    md = [f"# FROZEN PROTOCOL\n", f"Frozen {proto['frozen_at']} at commit `{sha}`.",
          "\nNo confirmatory family was run before this file existed. Every choice below was made on",
          "dev families (F01-F12, P01-P06) only.\n",
          f"- **Compactor**: `{proto['compactor']}`, T={proto['T']}, budget B={proto['B']} words, K={proto['K']} steps",
          f"- **Primary endpoint**: k={proto['primary_endpoint_k']}; checkpoints {proto['checkpoints']}",
          f"- **Seeds**: {proto['n_seeds']}",
          f"- **O3 slot count** (amendment A3): {proto['slots']}, realized stored length "
          f"{sel['O3']['stored_words']:.0f} words vs O1's {sel['W1_stored_words']:.0f} "
          f"(within 10% tolerance: {proto['O3_within_tolerance']})",
          f"- **O3 is described as**: {proto['O3_label']}",
          f"- **Empirical adequacy** (replaces 'compression is biting'): O1 retention@10 "
          f"{sel['adequacy']['retention_O1']:.3f}, O7 ceiling {sel['adequacy']['retention_O7']:.3f}, "
          f"gap {sel['adequacy']['gap_pp']:.1f} pp -> adequate: {sel['adequacy']['adequate']}",
          f"- **E-SHIFT**: {frames['n_eligible']} eligible families (r={frames['eligible_fraction_r']:.2f}), "
          f"threshold {frames['min_shift']} log-odds on elicitation Half A, achieved shift estimated "
          f"on the independent Half B; operative SESOI "
          f"{proto['eshift']['operative_sesoi_pp']:.1f} pp",
          "\n## Analysis, frozen\n"]
    for k, v in proto["analysis"].items():
        md.append(f"- **{k}**: {v}")
    (ROOT / "FROZEN_PROTOCOL.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
