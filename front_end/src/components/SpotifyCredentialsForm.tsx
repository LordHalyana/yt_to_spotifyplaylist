import React from 'react';
import { Box, TextField } from '@mui/material';

interface Props {
  value: { clientId: string; clientSecret: string };
  onChange: (val: { clientId: string; clientSecret: string }) => void;
}

export default function SpotifyCredentialsForm({ value, onChange }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400, mx: 'auto' }}>
      <TextField
        label="Spotify Client ID"
        value={value.clientId}
        onChange={e => onChange({ ...value, clientId: e.target.value })}
        fullWidth
      />
      <TextField
        label="Spotify Client Secret"
        value={value.clientSecret}
        onChange={e => onChange({ ...value, clientSecret: e.target.value })}
        fullWidth
        type="password"
      />
    </Box>
  );
}
