import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1f76ff',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#f38b00',
      contrastText: '#0b1f3a',
    },
    background: {
      default: '#f4f7fb',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: ['"Inter"', '"Roboto"', '"Helvetica"', 'Arial', 'sans-serif'].join(','),
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: '1px solid #e0e7ff',
          boxShadow: '0px 10px 30px rgba(15, 23, 42, 0.08)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(120deg, #051433, #12264e)',
        },
      },
    },
  },
});

export default theme;
