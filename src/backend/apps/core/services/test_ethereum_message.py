import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from apps.core.services.ethereum_message import prepare_ethereum_message


class EthereumFileMessageTests(unittest.TestCase):
    def setUp(self):
        self.instance = SimpleNamespace(
            bpmn=SimpleNamespace(
                eth_environment_id="env", name="SupplyChain",
                firefly_url="http://firefly:5000/api/v1/namespaces/default/apis/workflow",
                bpmnContent='''<definitions xmlns="urn:bpmn" xmlns:abc="urn:abc">
                  <message id="Message_1"><extensionElements><abc:MessageSchema>
                    <abc:File name="waybill" required="true" />
                  </abc:MessageSchema></extensionElements></message>
                  <messageFlow messageRef="Message_1" targetRef="buyer" />
                </definitions>''',
            ),
            execution_bindings={"participants": {"buyer": {"ethereum_identity_id": "identity"}}},
        )
        self.lookup = Mock(return_value=SimpleNamespace(firefly_identity_id="ff-identity"))
        self.upload = io.BytesIO(b"waybill contents")
        self.upload.name = "waybill.pdf"
        self.upload.content_type = "application/pdf"

    def prepare(self, uploads=None):
        return prepare_ethereum_message(
            self.instance, "Message_1",
            {"instanceId": 1, "fireflyTranId": "placeholder", "waybill": "sample.dat", "price": 2},
            uploads if uploads is not None else {"waybill": self.upload}, self.lookup,
        )

    @patch("apps.core.services.ethereum_message.requests.request")
    def test_upload_and_private_message_use_real_ids(self, request):
        request.side_effect = [Mock(ok=True, json=Mock(return_value={"did": "did:firefly:buyer"})),
                               Mock(ok=True, json=Mock(return_value={"id": "data-id"})),
                               Mock(ok=True, json=Mock(return_value={"header": {"id": "message-id"}}))]
        self.assertEqual(self.prepare(), {"messageId": "message-id", "fileIds": {"waybill": "data-id"}})
        self.lookup.assert_called_once_with({"ethereum_identity_id": "identity"}, "env")
        upload_call = request.call_args_list[1]
        self.assertEqual(upload_call.args[1], "http://firefly:5000/api/v1/namespaces/default/data")
        self.assertIs(upload_call.kwargs["files"]["file"][1], self.upload)
        message = request.call_args_list[2].kwargs["json"]
        self.assertEqual(message["data"], [{"value": {"waybill": "data-id", "price": 2}}, {"id": "data-id"}])
        self.assertEqual(message["group"]["members"], [{"identity": "did:firefly:buyer"}])

    @patch("apps.core.services.ethereum_message.requests.request")
    def test_missing_required_file_makes_no_firefly_request(self, request):
        with self.assertRaisesRegex(ValueError, "waybill is required"):
            self.prepare({})
        request.assert_not_called()

    @patch("apps.core.services.ethereum_message.requests.request")
    def test_missing_receiver_makes_no_firefly_request(self, request):
        self.lookup.return_value = None
        with self.assertRaisesRegex(ValueError, "bound FireFly identity"):
            self.prepare()
        request.assert_not_called()

    @patch("apps.core.services.ethereum_message.requests.request")
    def test_upload_failure_prevents_message_send(self, request):
        request.side_effect = [Mock(ok=True, json=Mock(return_value={"did": "did:firefly:buyer"})),
                               Mock(ok=False, status_code=500, text="upload failed")]
        with self.assertRaisesRegex(ValueError, "upload failed"):
            self.prepare()
        self.assertEqual(request.call_count, 2)

    @patch("apps.core.services.ethereum_message.requests.request")
    def test_legacy_documentation_schema(self, request):
        self.instance.bpmn.bpmnContent = '''<definitions><message id="Message_1"><documentation>
          {"files":{"waybill":{"type":"file"}},"file required":["waybill"]}
          </documentation></message></definitions>'''
        with self.assertRaisesRegex(ValueError, "waybill is required"):
            self.prepare({})
        request.assert_not_called()
