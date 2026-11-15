from pathlib import Path
import numpy as np
import pandas as pd
from agentflow_data_agent.core.agent import AutonomousDataAgent


def run_smoke_tests():
    """Runs a 4-scenario end-to-end multi-task smoke test suite."""
    print("=" * 75)
    print("AgentFlow Enterprise Autonomous Universal Data Agent (v4.0 Apex)")
    print("Multi-Task Verification & End-to-End Stress Test Suite")
    print("=" * 75)

    rng = np.random.RandomState(42)
    n = 1500

    print("\n--- [SCENARIO 1: TELECOM CHURN (IMBALANCED BINARY CLASSIFICATION)] ---")
    churn_df = pd.DataFrame({
        "customer_id": [f"CUST_{10000 + i}" for i in range(n)],
        "signup_date": pd.date_range("2023-01-01", periods=n, freq="h").astype(str),
        "monthly_spend": [f"${val:,.2f}" if i % 15 != 0 else "?" for i, val in enumerate(rng.exponential(120, n))],
        "tenure_months": rng.randint(1, 72, size=n),
        "support_tickets": rng.poisson(1.8, size=n),
        "plan_tier": rng.choice(["Basic", "Pro", "Enterprise", "N/A"], size=n, p=[0.5, 0.3, 0.15, 0.05]),
        "region_code": [f"REG_{rng.randint(1, 35)}" for _ in range(n)],
        "customer_feedback": rng.choice([
            "Great platform reliability and fast customer support response",
            "Billing issue and frequent dashboard lag during peak hours",
            "Very happy with the automated workflow features and analytics",
            "Too expensive for small teams cancelling subscription soon",
            "?"
        ], size=n),
        "constant_flag": ["ACTIVE"] * n,
        "churn": rng.choice([0, 1], size=n, p=[0.82, 0.18]),
    })

    demo_csv = Path("./artifacts/demo_messy_churn.csv")
    demo_csv.parent.mkdir(parents=True, exist_ok=True)
    churn_df.to_csv(demo_csv, index=False)

    agent = AutonomousDataAgent(output_dir="./artifacts/data_agent_demo")
    report = agent.run(
        file_path=demo_csv,
        project_id="demo_churn_001",
        problem_statement="Predict customer churn based on billing and support activity",
    )

    print(f"[SUCCESS] Completed in {report.execution_time_seconds}s")
    print(f"Selected Target     : {report.target_report.selected_target} ({report.target_report.inferred_problem_type})")
    print(f"Confidence Score    : {report.target_report.confidence_score * 100:.1f}%")
    print(f"Dataset Health      : {report.health_metrics.overall_health_score}/100 (Grade: {report.health_metrics.health_grade})")
    print(f"Features Progression: {report.preprocessing_summary.features_count_before_preprocess} raw -> "
          f"{report.preprocessing_summary.features_count_after_expansion} expanded -> "
          f"{report.preprocessing_summary.features_count_final} final")
    print(f"SMOTE Applied       : {report.preprocessing_summary.smote_applied} "
          f"(+{report.preprocessing_summary.smote_synthetic_samples_added} synthetic rows on train)")
    print(f"Recommended Models  : {', '.join(report.strategy_handoff.recommended_candidate_models[:3])}")
    print(f"Primary Metric      : {report.strategy_handoff.primary_evaluation_metric}")
    print(f"Actionable Remediations: {report.health_metrics.actionable_remediations[:2]}")

    print("\n--- [SCENARIO 2: PRODUCTION STREAMING WITH SCHEMA PERTURBATION & DRIFT] ---")
    unseen_sample = churn_df.drop(columns=["churn"]).head(8).copy()
    unseen_sample.drop(columns=["support_tickets"], inplace=True)
    unseen_sample["unexpected_partner_code"] = ["PARTNER_XYZ"] * len(unseen_sample)

    transformed_unseen, drift_report = agent.transform_unseen_data(unseen_sample, compute_drift=True)
    print(f"[SUCCESS] Transformed perturbed unseen stream: shape={transformed_unseen.shape}")
    assert not transformed_unseen.isna().any().any(), "Unseen data contains NaN values!"
    print("[ASSERTION PASSED] Zero NaN values in unseen inference output.")
    print(f"[DRIFT MONITORING] Average PSI: {drift_report.average_psi:.4f} (Drift Detected: {drift_report.drift_detected})")

    print("\n--- [SCENARIO 3: REAL ESTATE PRICING (CONTINUOUS REGRESSION)] ---")
    reg_df = pd.DataFrame({
        "house_id": [f"H_{i}" for i in range(800)],
        "sqft_living": rng.normal(2000, 500, size=800).clip(500, 6000),
        "bedrooms": rng.choice([1, 2, 3, 4, 5], size=800, p=[0.05, 0.2, 0.5, 0.2, 0.05]),
        "zipcode": [f"ZIP_{rng.randint(98001, 98050)}" for _ in range(800)],
        "year_built": rng.randint(1950, 2024, size=800),
        "saleprice": rng.exponential(350000, size=800) + 150000,
    })
    reg_csv = Path("./artifacts/demo_housing_reg.csv")
    reg_df.to_csv(reg_csv, index=False)

    reg_agent = AutonomousDataAgent(output_dir="./artifacts/data_agent_demo")
    reg_report = reg_agent.run(
        file_path=reg_csv,
        project_id="demo_housing_002",
        problem_statement="Forecast housing sale price based on square footage and features",
    )
    print(f"[SUCCESS] Completed in {reg_report.execution_time_seconds}s")
    print(f"Selected Target     : {reg_report.target_report.selected_target} ({reg_report.target_report.inferred_problem_type})")
    print(f"Primary Metric      : {reg_report.strategy_handoff.primary_evaluation_metric}")
    print(f"Recommended Models  : {', '.join(reg_report.strategy_handoff.recommended_candidate_models[:3])}")
    print(f"Strategy Notes      : {reg_report.strategy_handoff.strategy_notes}")

    print("\n--- [SCENARIO 4: CUSTOMER SEGMENTATION (MULTICLASS CLASSIFICATION)] ---")
    multi_df = pd.DataFrame({
        "user_id": [f"U_{i}" for i in range(900)],
        "session_count": rng.poisson(12, size=900),
        "cart_value": rng.exponential(85, size=900),
        "device_type": rng.choice(["iOS", "Android", "Desktop", "Tablet"], size=900),
        "customer_segment": rng.choice(["Bronze", "Silver", "Gold", "Platinum"], size=900, p=[0.45, 0.30, 0.15, 0.10]),
    })
    multi_csv = Path("./artifacts/demo_customer_multiclass.csv")
    multi_df.to_csv(multi_csv, index=False)

    multi_agent = AutonomousDataAgent(output_dir="./artifacts/data_agent_demo")
    multi_report = multi_agent.run(
        file_path=multi_csv,
        project_id="demo_multiclass_003",
        problem_statement="Classify customers into bronze, silver, gold, and platinum tiers",
    )
    print(f"[SUCCESS] Completed in {multi_report.execution_time_seconds}s")
    print(f"Selected Target     : {multi_report.target_report.selected_target} ({multi_report.target_report.inferred_problem_type})")
    print(f"Class Distribution  : {multi_report.target_report.class_distribution}")
    print(f"Primary Metric      : {multi_report.strategy_handoff.primary_evaluation_metric}")
    print(f"Recommended Models  : {', '.join(multi_report.strategy_handoff.recommended_candidate_models[:3])}")

    print("\n" + "=" * 75)
    print("ALL 4 SCENARIOS PASSED WITH 100% SUCCESS — AGENTFLOW DATA AGENT READY!")
    print("=" * 75)
