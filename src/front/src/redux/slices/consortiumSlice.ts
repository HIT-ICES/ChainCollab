import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootStateType, DispatchType } from '../store'


interface consortiumState {
    currentConsortiumId: string,
    currentConsortiumName: string,
    currentConsortiumType: string,
}

const initialState: consortiumState = {
    currentConsortiumId: "",
    currentConsortiumName: "",
    currentConsortiumType: "standard" // Default type can be 'standard' or 'ssi'
}

/**
 * Represents the user slice of the Redux store.
 */
export const consortiumSlice = createSlice({
    name: 'consortium',
    initialState,
    reducers: {
        activateConsortium: (state, action: PayloadAction<
            {
                currentConsortiumId: string,
                currentConsortiumName: string,
                currentConsortiumType: string
            }>) => {
            return {
                currentConsortiumId: action.payload.currentConsortiumId,
                currentConsortiumName: action.payload.currentConsortiumName,
                currentConsortiumType: action.payload.currentConsortiumType
            }
        },
        deactivateConsortium: (state) => {
            return initialState;
        },
    }
})

export const {
    activateConsortium, deactivateConsortium
} = consortiumSlice.actions;

export const syncData = () => async (dispatch: DispatchType) => {
    // Turn deactivate logic into here, when activate and deactivae, deactivate the subresources
}

export const selectConsortium = (state: RootStateType) => state.consortium;
export default consortiumSlice.reducer