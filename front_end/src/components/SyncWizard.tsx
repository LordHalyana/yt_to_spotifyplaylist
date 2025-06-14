import React from 'react';
import { Box, Stepper, Step, StepLabel, Button, Typography } from '@mui/material';
import SpotifyCredentialsForm from './SpotifyCredentialsForm';
import SyncConfigForm from './SyncConfigForm';
import SyncLogSSE from './SyncLogSSE';

const steps = ['Spotify Credentials', 'Sync Config', 'Live Sync Log'];

export default function SyncWizard() {
  const [activeStep, setActiveStep] = React.useState(0);
  const [spotifyCreds, setSpotifyCreds] = React.useState({ clientId: '', clientSecret: '' });
  const [syncConfig, setSyncConfig] = React.useState({ ytUrl: '', spotifyPlaylistId: '' });
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleNext = async () => {
    setError(null);
    if (activeStep === 1) {
      setLoading(true);
      try {
        const response = await fetch('http://localhost:8000/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            spotify: spotifyCreds,
            youtube: { url: syncConfig.ytUrl },
            spotifyPlaylistId: syncConfig.spotifyPlaylistId,
          }),
        });
        if (!response.ok) throw new Error('Failed to start sync');
        const data = await response.json();
        if (!data.job_id) throw new Error('No job_id returned');
        setJobId(data.job_id);
        setActiveStep((prev) => prev + 1);
      } catch (e: unknown) {
        if (e instanceof Error) {
          setError(e.message);
        } else {
          setError('Unknown error');
        }
      } finally {
        setLoading(false);
      }
      return;
    }
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  return (
    <Box sx={{ width: '100%', mt: 4 }}>
      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      <Box sx={{ mt: 4 }}>
        {activeStep === 0 && (
          <SpotifyCredentialsForm value={spotifyCreds} onChange={setSpotifyCreds} />
        )}
        {activeStep === 1 && (
          <SyncConfigForm value={syncConfig} onChange={setSyncConfig} />
        )}
        {activeStep === 2 && jobId && <SyncLogSSE jobId={jobId} />}
        {error && (
          <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>
        )}
        <Box sx={{ display: 'flex', flexDirection: 'row', pt: 2 }}>
          <Button color="inherit" disabled={activeStep === 0 || loading} onClick={handleBack} sx={{ mr: 1 }}>
            Back
          </Button>
          <Box sx={{ flex: '1 1 auto' }} />
          {activeStep < steps.length - 1 && (
            <Button onClick={handleNext} disabled={loading}>
              {loading && activeStep === 1 ? 'Starting...' : 'Next'}
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
}
