import { configureStore } from '@reduxjs/toolkit'
import { userSlice } from './slices/userSlice'
import { orgSlice } from './slices/orgSlice'
import { consortiumSlice } from './slices/consortiumSlice'
import { envSlice } from './slices/envSlice'
import { UISlice } from './slices/UISlice'
import { MembershipSlice } from './slices/MemershipSlice'

const rootReducer = {
  user: userSlice.reducer,
  org: orgSlice.reducer,
  consortium: consortiumSlice.reducer,
  env: envSlice.reducer,
  ui: UISlice.reducer,
  membership: MembershipSlice.reducer 
}


/**
 * The Redux store.
 */
export const store = configureStore({
  reducer: {
    ...rootReducer,
  },
})

export type RootStateType = ReturnType<typeof store.getState>
export type DispatchType = typeof store.dispatch