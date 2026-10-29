# ChainCollab translator

Active release modules: `generator/` (CIM parser and projection), `DSL/B2CDSL/`,
`CodeGenerator/b2cdsl-go/`, `CodeGenerator/b2cdsl-solidity/` (real Jinja templates),
and `service/api.py` (FastAPI on 9999). The development MDAcheck, dashboard and
saved build outputs are retained on the development branches.

Use the repository [startup guide](../../Readme.md):
`python3 scripts/chaincollab.py setup`, then `up`.
The standalone generation commands and structured examples are documented there.
The three editable packages must be installed in this component's own environment.
