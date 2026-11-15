import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentflow_data_agent.core.agent import AutonomousDataAgent
from agentflow_data_agent.tests.smoke_test import run_smoke_tests


def main():
    parser = argparse.ArgumentParser(description="AgentFlow Enterprise Autonomous Universal Data Agent (v4.0 Apex)")
    parser.add_argument("--file", type=str, help="Path to raw dataset file (CSV, TSV, Parquet, JSON, SQLite, ZIP)")
    parser.add_argument("--target", type=str, default=None, help="Optional explicit target column name")
    parser.add_argument("--problem", type=str, default=None, help="Optional natural language problem statement")
    parser.add_argument("--output-dir", type=str, default="./artifacts/data_agent_run", help="Artifacts directory")
    parser.add_argument("--project-id", type=str, default="agentflow_run_001", help="Unique project identifier")
    parser.add_argument("--test-suite", action="store_true", help="Execute multi-task smoke verification suite")

    args = parser.parse_args()

    if args.file:
        agent = AutonomousDataAgent(output_dir=args.output_dir)
        report = agent.run(
            file_path=args.file,
            project_id=args.project_id,
            target_column=args.target,
            problem_statement=args.problem,
        )
        print("\n[AGENTFLOW DATA AGENT RUN COMPLETED]")
        print(f"Report Artifact : {report.artifact_paths.report_json_path}")
        print(f"Train Artifact  : {report.artifact_paths.processed_train_path}")
        print(f"Test Artifact   : {report.artifact_paths.processed_test_path}")
        print(f"Pipeline Pickle : {report.artifact_paths.pipeline_pickle_path}")
        print(f"Target Selected : {report.target_report.selected_target} ({report.target_report.inferred_problem_type})")
        print(f"Dataset Health  : {report.health_metrics.overall_health_score}/100 ({report.health_metrics.health_grade})")
    else:
        run_smoke_tests()


if __name__ == "__main__":
    main()
