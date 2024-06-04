func (cc *SmartContract) RegisterParticipant(ctx contractapi.TransactionContextInterface, instanceID string, targetParticipantID string) error {
	{
		// check if the participant is single
		var targetParticipant Participant
		participant, _ := cc.ReadParticipant(ctx, instanceID, targetParticipantID)
		if participant.IsMulti {
			{
				return fmt.Errorf("The participant is not multi")
			}
		}

		// Read the identity of invoker ,and binding it's identity to the participant

		// Get the identity of the invoker
		invokerIdentity, err := ctx.GetClientIdentity().GetID()
		mspIndentity, err := ctx.GetClientIdentity().GetMSPID()

		X509 := invokerIdentity + "@" + mspIndentity

		// save the identity to the participant
		targetParticipant.X509 = X509

		// save the participant
		err = cc.WriteParticipant(ctx, instanceID, targetParticipantID, &targetParticipant)
		if err != nil {
			{
				return err
			}
		}

		return nil
	}
}