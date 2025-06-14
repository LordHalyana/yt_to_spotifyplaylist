import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

interface Props {
  jobId: string;
}

export default function SyncLogSSE({ jobId }: Props) {
  const [log, setLog] = React.useState<string[]>([]);
  React.useEffect(() => {
    const eventSource = new EventSource(`http://localhost:8000/sync/${jobId}`);
    eventSource.onmessage = (e) => {
      setLog((prev) => [...prev, e.data]);
    };
    eventSource.onerror = () => {
      eventSource.close();
    };
    return () => {
      eventSource.close();
    };
  }, [jobId]);

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h6" gutterBottom>Live Sync Log</Typography>
      <Paper variant="outlined" sx={{ p: 2, minHeight: 200, maxHeight: 300, overflow: 'auto', bgcolor: '#111', color: '#0f0', fontFamily: 'monospace' }}>
        {log.length === 0 ? <span>No log yet.</span> : log.map((line, i) => <div key={i}>{line}</div>)}
      </Paper>
    </Box>
  );
}
