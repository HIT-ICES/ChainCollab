import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import parse_b2c_file, parse_bpmn_file, verify_mapping
from common import generate_b2c_with_newtranslator


class Exp1SmokeTest(unittest.TestCase):
    def _generate_and_verify(self, case_name: str, bpmn: Path, dmn: Path | None = None):
        output = ROOT / "outputs" / "regenerated" / f"{case_name}.test.generated.b2c"
        report = verify_mapping(
            parse_bpmn_file(bpmn, dmn, case_name),
            parse_b2c_file(generate_b2c_with_newtranslator(bpmn, output, contract_name=case_name), case_name),
        )
        return report

    def test_supply_chain_baseline_passes(self):
        bpmn = Path("/root/code/ChainCollab/Experiment/BPMNwithDMNcase/SupplyChainPaper7777.bpmn")
        dmn = Path("/root/code/ChainCollab/Experiment/BPMNwithDMNcase/supplyChainPaper.dmn")
        report = self._generate_and_verify("SupplyChainPaper7777", bpmn, dmn)
        self.assertEqual(report["contract_satisfaction_rate"], 1.0)
        self.assertTrue(report["pass"])

    def test_customer_new_passes(self):
        bpmn = Path("/root/code/ChainCollab/Experiment/BPMNwithDMNcase/customer_new.bpmn")
        dmn = Path("/root/code/ChainCollab/Experiment/BPMNwithDMNcase/customer.dmn")
        report = self._generate_and_verify("customer_new", bpmn, dmn)
        self.assertEqual(report["contract_satisfaction_rate"], 1.0)
        self.assertTrue(report["pass"])

    def test_incident_management_passes(self):
        bpmn = Path("/root/code/ChainCollab/Experiment/CaseTest/IncidentManagement.bpmn")
        report = self._generate_and_verify("IncidentManagement", bpmn, None)
        self.assertEqual(report["contract_satisfaction_rate"], 1.0)
        self.assertTrue(report["pass"])

    def test_management_system_passes(self):
        bpmn = Path("/root/code/ChainCollab/Experiment/BPMNwithDMNcase/ManagementSystem_new3.bpmn")
        dmn = Path("/root/code/ChainCollab/Experiment/BPMNwithDMNcase/management.dmn")
        report = self._generate_and_verify("ManagementSystem", bpmn, dmn)
        self.assertEqual(report["contract_satisfaction_rate"], 1.0)
        self.assertTrue(report["pass"])


if __name__ == "__main__":
    unittest.main()
