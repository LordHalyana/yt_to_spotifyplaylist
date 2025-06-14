import React from 'react';
import { Box, TextField } from '@mui/material';

interface Props {
  value: { ytUrl: string; spotifyPlaylistId: string };
  onChange: (val: { ytUrl: string; spotifyPlaylistId: string }) => void;
}

export default function SyncConfigForm({ value, onChange }: Props) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400, mx: 'auto' }}>
      <TextField
        label="YouTube Playlist URL"
        value={value.ytUrl}
        onChange={e => onChange({ ...value, ytUrl: e.target.value })}
        fullWidth
      />
      <TextField
        label="Spotify Playlist ID"
        value={value.spotifyPlaylistId}
        onChange={e => onChange({ ...value, spotifyPlaylistId: e.target.value })}
        fullWidth
      />
    </Box>
  );
}
