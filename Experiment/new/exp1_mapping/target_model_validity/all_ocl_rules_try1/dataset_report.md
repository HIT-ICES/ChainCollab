# Balanced Dataset Report

- Total samples: 151
- positive: 11
- targeted_negative: 140

## Assigned Rule Counts

- targeted_negative:BusinessRule::InputMappingParamUnique: 10
- targeted_negative:BusinessRule::OutputMappingParamUnique: 10
- targeted_negative:Contract::StartDoesNotEnableItself: 10
- targeted_negative:Contract::UniqueNamesPerKind: 10
- targeted_negative:GatewayCompareBranch::CompareLiteralTypeMatchesGlobalType: 10
- targeted_negative:GatewayFlow::CompareBranchesNoDuplicateConditions: 10
- targeted_negative:Message::SenderNotReceiver: 10
- targeted_negative:Model::AtLeastOneContract: 10
- targeted_negative:Model::UniqueContractNames: 10
- targeted_negative:Participant::AttributeKeysUnique: 10
- targeted_negative:Participant::MspX509Paired: 10
- targeted_negative:Participant::MultiBoundsOrder: 10
- targeted_negative:Participant::MultiBoundsPaired: 10
- targeted_negative:SetGlobalAction::SetLiteralTypeMatchesGlobalType: 10

See `dataset_manifest.json` for per-sample metadata.
