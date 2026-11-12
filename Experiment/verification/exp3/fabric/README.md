# Fabric replay

[replay_fabric_instance.py](../scripts/replay_fabric_instance.py) invokes a deployed Fabric workflow through FireFly using a [shared logical path](../cases/). [run_fabric_case_paths.py](../scripts/run_fabric_case_paths.py) runs a case batch. Configure the deployed API, participant identities, and rule services before replay.

Each case retains raw replay records and, where available, batch summaries. [compare_fabric_replay.py](../scripts/compare_fabric_replay.py) normalizes Fabric records and produces the DSL–Fabric and Geth–Fabric comparisons in [outputs](../outputs/).
