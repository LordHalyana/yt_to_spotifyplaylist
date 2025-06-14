import { Container, CssBaseline, Typography, Box } from '@mui/material';
import SyncWizard from './components/SyncWizard';

function App() {
  return (
    <Container maxWidth="md">
      <CssBaseline />
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          YouTube to Spotify Sync Wizard
        </Typography>
        <SyncWizard />
      </Box>
    </Container>
  );
}

export default App
