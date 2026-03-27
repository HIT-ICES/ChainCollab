import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { RootStateType, DispatchType } from '../store'


//API
import { login, register } from '../../api/loginAPI'


// interface Preference {
//     last_active_org: string,
//     last_active_consortium: string,
//     last_active_env: string,
// }

interface UserInfo {
    username: string,
    email: string,
    role: string,
    id: string,
}


interface UserState {
    userInfo: UserInfo,
    loginStatus: 'idle' | 'login' | 'success' | 'failed',
    registerStatus: 'idle' | 'register' | 'success' | 'failed',
}

interface LoginPayload {
    username: string,
    email: string,
    role: string,
    id: string,
}

// 使用该类型定义初始 state
const initialState: UserState = {
    userInfo: {
        username: '',
        email: '',
        role: '',
        id: '',
    },
    loginStatus: 'idle',
    registerStatus: 'idle'
}

/**
 * Represents the user slice of the Redux store.
 */
export const userSlice = createSlice({
    name: 'user',
    initialState,
    reducers: {
        /**
         * Updates the login status to 'login'.
         * @param state - The current state of the user slice.
         * @returns The updated state with the login status set to 'login'.
         */
        loginStart: (state) => {
            return { ...state, loginStatus: 'login' }
        },
        /**
         * Updates the login status to 'success' and sets the email and username based on the provided payload.
         * @param state - The current state of the user slice.
         * @param action - The payload containing the email.
         * @returns The updated state with the login status set to 'success', email updated, and username derived from the email.
         */
        loginSuccess: (state, action: PayloadAction<LoginPayload>) => {
            return {
                ...state,
                userInfo: {
                    email: action.payload.email,
                    username: action.payload.username,
                    role: action.payload.role,
                    id: action.payload.id,
                    orgs: [],
                },
                loginStatus: 'success',
            }
        },
        /**
         * Updates the login status to 'failed'.
         * @param state - The current state of the user slice.
         * @returns The updated state with the login status set to 'failed'.
         */
        loginFailed: (state) => {
            return { ...state, loginStatus: 'failed' }
        },
        /**
         * Updates the login status to 'idle' and clears the email and username.
         * @param state - The current state of the user slice.
         * @returns The updated state with the login status set to 'idle', email cleared, and username cleared.
         */
        logout: (state) => {
            return { ...initialState, registerStatus: state.registerStatus, loginStatus: 'idle' }
        },

        // Register Related
        registerStart: (state) => {
            return { ...state, registerStatus: 'register' }
        },
        registerSuccess: (state) => {
            return { ...state, registerStatus: 'success' }
        },
        registerFailed: (state) => {
            return { ...state, registerStatus: 'failed' }
        },
        registerReset: (state) => {
            return { ...state, registerStatus: 'idle' }
        }

    }
})

export const { loginStart, loginSuccess, loginFailed, logout,
    registerStart, registerSuccess, registerFailed, registerReset
} = userSlice.actions;

export const loginAction = (email: string, password: string) => async (dispatch: DispatchType) => {
    try {
        dispatch(loginStart());
        const result = await login(email, password);
        if (result.isSuccess) {
            dispatch(loginSuccess({
                username: result.username,
                email: result.email,
                role: result.role,
                id: result.id,
            }));
        } else {
            dispatch(loginFailed());
        }
    } catch (err) {
        dispatch(loginFailed());
    }
}


// Register
export const registerUserAction = (name: string, email: string, password: string) => async (dispatch: DispatchType) => {
    dispatch(registerStart())
    const result = await register(
        email, name, password
    )
    if (result === true) {
        dispatch(
            registerSuccess()
        )
    } else {
        dispatch(
            registerFailed()
        )
    }
}

import { deactivateConsortium } from './consortiumSlice';
import { deactivateOrg } from './orgSlice';
import { deactivateEnv } from './envSlice';

export const logoutAction = () => (dispatch: DispatchType) => {
    dispatch(logout());
    dispatch(deactivateConsortium());
    dispatch(deactivateOrg());
    dispatch(deactivateEnv());
}


export const selectUser = (state: RootStateType) => state.user;
export default userSlice.reducer
