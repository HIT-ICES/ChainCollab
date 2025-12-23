import { AppBar, Box, Container, Toolbar, Typography } from '@mui/material';
import { ThemeProvider, CssBaseline } from '@mui/material';
import TranslatorWorkbench from './components/TranslatorWorkbench';
import theme from './theme';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh' }}>
        <AppBar position="static" elevation={0}>
          <Toolbar sx={{ justifyContent: 'space-between' }}>
            <Typography variant="h6" component="div">
              Translator Console
            </Typography>
            <Typography variant="body2" color="primary.contrastText">
              Material × AWS Inspired Dashboard
            </Typography>
          </Toolbar>
        </AppBar>
        <Container maxWidth="lg" sx={{ py: 5 }}>
          <TranslatorWorkbench />
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
