import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootStateType, DispatchType } from '../store'


interface MemState {
    currentMemId: string,
    currentMemName: string,
    currentMemType: string
}

const initialState: MemState = {
    currentMemId: '',
    currentMemName: '',
    currentMemType: ''
}

export const MembershipSlice = createSlice({
    name: 'membership',
    initialState,
    reducers: {
        activateMem: (state, action: PayloadAction<{
            currentMemId: string,
            currentMemName: string,
            currentMemType: string
        }>) => {
            return {
                currentMemId: action.payload.currentMemId,
                currentMemName: action.payload.currentMemName,
                currentMemType: action.payload.currentMemType
            }
        },
        deactivateMem: (state) => {
            return initialState;
        }
    }
})

export const {
    activateMem, deactivateMem
} = MembershipSlice.actions;

export const selectOrg = (state: RootStateType) => state.org;
export default MembershipSlice.reducer