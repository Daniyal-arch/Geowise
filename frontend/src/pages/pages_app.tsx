import '../styles/globals.css';
import type { AppProps } from 'next/app';
import { useState } from 'react';
import { QueryClient, QueryClientProvider, Hydrate } from '@tanstack/react-query';

// Optionally import maplibre CSS here so styles are present without importing maplibre JS on server
import 'maplibre-gl/dist/maplibre-gl.css';

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <Hydrate state={(pageProps as any)?.dehydratedState}>
        <Component {...pageProps} />
      </Hydrate>
    </QueryClientProvider>
  );
}