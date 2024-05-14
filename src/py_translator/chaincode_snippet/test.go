	currentMemory, err := cc.ReadGlobalVariable(ctx)
	if err != nil {
		return err
	}
