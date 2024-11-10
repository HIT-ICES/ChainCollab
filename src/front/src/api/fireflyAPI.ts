
export const getMessageWithId = async (url:string, id: string) => {
    const response = await fetch(`${url}/api/v1/messages/${id}`);
    return response.json();
}

// {
//     "header": {
//       "id": "677c5c95-7ad7-48ec-b3dc-ebd403ef9169",
//       "type": "private",
//       "txtype": "batch_pin",
//       "author": "did:firefly:org/org_4c078a",
//       "key": "Logres.org.comMSP::x509::CN=org_4c078a,OU=client::CN=ca.Logres.org.com,OU=Fabric,O=Logres.org.com,ST=North Carolina,C=US",
//       "created": "2024-11-10T11:02:44.855930993Z",
//       "namespace": "default",
//       "group": "57ad35515a8ae984bd7242628af9b5980fa6a8bdc6c221047fb9fd97970abbe6",
//       "topics": [
//         "Supply.bpmn_Message_1wswgqu"
//       ],
//       "tag": "private",
//       "datahash": "169ae2760afd2a7611abd865b03bd7a6c686cb8d296cae61b76ea55dbe7ea449"
//     },
//     "localNamespace": "default",
//     "hash": "9403f4f454894551967e2b3fe244fb29a6b868325989c5cdce07ee92198fd3ff",
//     "batch": "d8ef6ca8-e11b-4c56-8ac7-2368d3eeabc5",
//     "state": "sent",
//     "data": [
//       {
//         "id": "e79824da-a231-4849-a129-bafe596016fb",
//         "hash": "1a6b479fab26011cc11ff2a371c62f282f3bb4b9549f97f39903786b49d53a40"
//       }
//     ],
//     "pins": [
//       "6f6959572394b722c337646e5c7a01da22a0d5be95bfe0865616f077480936b1:0000000000000001"
//     ]
//   }

// http://127.0.0.1:5002/api/v1/batches/d8ef6ca8-e11b-4c56-8ac7-2368d3eeabc5

export const getBatchWithId = async (url:string, id: string) => {
    const response = await fetch(`${url}/api/v1/batches/${id}`);
    return response.json();
}

// {
//     "id": "d8ef6ca8-e11b-4c56-8ac7-2368d3eeabc5",
//     "type": "private",
//     "namespace": "default",
//     "node": "3a080dc1-5aa7-4d38-bf4f-8e580a28a733",
//     "group": "57ad35515a8ae984bd7242628af9b5980fa6a8bdc6c221047fb9fd97970abbe6",
//     "created": "2024-11-10T11:02:45.865464939Z",
//     "author": "did:firefly:org/org_4c078a",
//     "key": "Logres.org.comMSP::x509::CN=org_4c078a,OU=client::CN=ca.Logres.org.com,OU=Fabric,O=Logres.org.com,ST=North Carolina,C=US",
//     "hash": "8dfa2d99fdd7823d662d8b254c6f0124f67526d3fe3fa64db493bdfc873d6b9f",
//     "manifest": {
//       "version": 1,
//       "id": "d8ef6ca8-e11b-4c56-8ac7-2368d3eeabc5",
//       "tx": {
//         "type": "batch_pin",
//         "id": "fece4cfb-665e-43d3-9e00-46f979cd4ad2"
//       },
//       "messages": [
//         {
//           "id": "677c5c95-7ad7-48ec-b3dc-ebd403ef9169",
//           "hash": "9403f4f454894551967e2b3fe244fb29a6b868325989c5cdce07ee92198fd3ff",
//           "topics": 1
//         }
//       ],
//       "data": [
//         {
//           "id": "e79824da-a231-4849-a129-bafe596016fb",
//           "hash": "1a6b479fab26011cc11ff2a371c62f282f3bb4b9549f97f39903786b49d53a40"
//         }
//       ]
//     },
//     "tx": {
//       "type": "batch_pin",
//       "id": "fece4cfb-665e-43d3-9e00-46f979cd4ad2"
//     },
//     "confirmed": null
//   }

// http://127.0.0.1:5002/api/v1/operations/5f63862c-c1f9-4dae-8e24-e3abbeac78e7?fetchstatus=true
export const getOperationWithId = async (url:string, id: string) => {
    const response = await fetch(`${url}/api/v1/operations/${id}?fetchstatus=true`);
    return response.json();
}

// {
//     "id": "5f63862c-c1f9-4dae-8e24-e3abbeac78e7",
//     "namespace": "default",
//     "tx": "2fc51e0c-818e-4454-9552-6fcdc47323f4",
//     "type": "blockchain_invoke",
//     "status": "Succeeded",
//     "plugin": "fabric",
//     "input": {
//       "input": {
//         "FireFlyTran": "677c5c95-7ad7-48ec-b3dc-ebd403ef9169",
//         "InstanceID": "1"
//       },
//       "interface": "eee3d64e-e239-4bde-acad-243d5b349a50",
//       "key": "Logres.org.comMSP::x509::CN=User1,OU=client::CN=ca.Logres.org.com,OU=Fabric,O=Logres.org.com,ST=North Carolina,C=US",
//       "location": {
//         "chaincode": "Supply",
//         "channel": "default"
//       },
//       "method": {
//         "description": "",
//         "id": "33bf04ec-a7bf-4314-8015-88ba2635c3c0",
//         "interface": "eee3d64e-e239-4bde-acad-243d5b349a50",
//         "name": "Message_1wswgqu_Send",
//         "namespace": "default",
//         "params": [
//           {
//             "name": "InstanceID",
//             "schema": {
//               "type": "string"
//             }
//           },
//           {
//             "name": "FireFlyTran",
//             "schema": {
//               "type": "string"
//             }
//           }
//         ],
//         "pathname": "Message_1wswgqu_Send",
//         "returns": []
//       },
//       "methodPath": "Message_1wswgqu_Send",
//       "options": null,
//       "type": "invoke"
//     },
//     "output": {
//       "headers": {
//         "requestId": "default:5f63862c-c1f9-4dae-8e24-e3abbeac78e7",
//         "type": "TransactionSuccess"
//       },
//       "transactionHash": "a2127c0f1d3c2b45a22692305094c9f05e98fce48c698be5530e2996930869fe"
//     },
//     "created": "2024-11-10T11:02:45.17888206Z",
//     "updated": "2024-11-10T11:02:45.17888206Z",
//     "detail": {
//       "error": "FF10284: Error from fabconnect: Must specify the channel"
//     }
//   }

//http://127.0.0.1:5002/api/v1/events?fetchreferences=true&fetchreference=true&tx=2fc51e0c-818e-4454-9552-6fcdc47323f4&limit=25
export const getEventWithTX = async (url:string, tx: string, type = "blockchain_invoke_op_succeeded" ) => {
    const response = await fetch(`${url}/api/v1/events?fetchreferences=true&fetchreference=true&tx=${tx}`);
    const events = await response.json();
    return events.filter((event) => event.type === type);
}

// [
//     {
//       "id": "34bae580-7915-4a33-b768-484d06fa4247",
//       "sequence": 127,
//       "type": "blockchain_invoke_op_succeeded",
//       "namespace": "default",
//       "reference": "5f63862c-c1f9-4dae-8e24-e3abbeac78e7",
//       "tx": "2fc51e0c-818e-4454-9552-6fcdc47323f4",
//       "created": "2024-11-10T11:02:47.319540685Z",
//       "operation": {
//         "id": "5f63862c-c1f9-4dae-8e24-e3abbeac78e7",
//         "namespace": "default",
//         "tx": "2fc51e0c-818e-4454-9552-6fcdc47323f4",
//         "type": "blockchain_invoke",
//         "status": "Succeeded",
//         "plugin": "fabric",
//         "input": {
//           "input": {
//             "FireFlyTran": "677c5c95-7ad7-48ec-b3dc-ebd403ef9169",
//             "InstanceID": "1"
//           },
//           "interface": "eee3d64e-e239-4bde-acad-243d5b349a50",
//           "key": "Logres.org.comMSP::x509::CN=User1,OU=client::CN=ca.Logres.org.com,OU=Fabric,O=Logres.org.com,ST=North Carolina,C=US",
//           "location": {
//             "chaincode": "Supply",
//             "channel": "default"
//           },
//           "method": {
//             "description": "",
//             "id": "33bf04ec-a7bf-4314-8015-88ba2635c3c0",
//             "interface": "eee3d64e-e239-4bde-acad-243d5b349a50",
//             "name": "Message_1wswgqu_Send",
//             "namespace": "default",
//             "params": [
//               {
//                 "name": "InstanceID",
//                 "schema": {
//                   "type": "string"
//                 }
//               },
//               {
//                 "name": "FireFlyTran",
//                 "schema": {
//                   "type": "string"
//                 }
//               }
//             ],
//             "pathname": "Message_1wswgqu_Send",
//             "returns": []
//           },
//           "methodPath": "Message_1wswgqu_Send",
//           "options": null,
//           "type": "invoke"
//         },
//         "output": {
//           "headers": {
//             "requestId": "default:5f63862c-c1f9-4dae-8e24-e3abbeac78e7",
//             "type": "TransactionSuccess"
//           },
//           "transactionHash": "a2127c0f1d3c2b45a22692305094c9f05e98fce48c698be5530e2996930869fe"
//         },
//         "created": "2024-11-10T11:02:45.17888206Z",
//         "updated": "2024-11-10T11:02:45.17888206Z"
//       }
//     },
//     {
//       "id": "9352c50a-2944-4a9e-b914-3e29d04784a9",
//       "sequence": 125,
//       "type": "transaction_submitted",
//       "namespace": "default",
//       "reference": "2fc51e0c-818e-4454-9552-6fcdc47323f4",
//       "tx": "2fc51e0c-818e-4454-9552-6fcdc47323f4",
//       "topic": "contract_invoke",
//       "created": "2024-11-10T11:02:45.178864488Z",
//       "transaction": {
//         "id": "2fc51e0c-818e-4454-9552-6fcdc47323f4",
//         "namespace": "default",
//         "type": "contract_invoke",
//         "created": "2024-11-10T11:02:45.17864881Z",
//         "blockchainIds": [
//           "a2127c0f1d3c2b45a22692305094c9f05e98fce48c698be5530e2996930869fe"
//         ]
//       }
//     }
//   ]
