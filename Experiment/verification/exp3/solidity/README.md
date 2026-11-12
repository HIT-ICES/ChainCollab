# Geth/Solidity replay

[replay_bound_eth_instance.py](../scripts/replay_bound_eth_instance.py) invokes the generated contract through FireFly. Configure the contract API, Ethereum signers, and the instance creation parameters using the [SupplyChainPaper template](SupplyChainPaper/replay_bound_eth_instance.template.json) as a starting point.

Use [materialize_logical_path.py](../scripts/materialize_logical_path.py) to derive an `execution_sequence.json` from a [shared logical path](../cases/). The case directories retain execution sequences and raw replay records. The normalized Geth traces and pairwise comparisons are in [outputs](../outputs/).
