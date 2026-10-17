import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { profileService } from '@/services/profileService';
import { Loading } from '@/components/common';
import { apiErrorMessage } from '@/hooks/useWorkspace';
import { PROFILE_KEY, ProfileContext } from '@/hooks/useProfile';

/** Loads the backend's market profile once; the app renders after it */
export const ProfileProvider = ({ children }: { children: ReactNode }) => {
  const query = useQuery({
    queryKey: PROFILE_KEY,
    queryFn: profileService.fetchProfile,
    staleTime: Infinity,
    retry: 2,
  });

  if (query.data) {
    return <ProfileContext.Provider value={query.data}>{children}</ProfileContext.Provider>;
  }
  return (
    <div className="flex h-screen items-center justify-center p-6">
      {query.error ? (
        <div className="max-w-lg space-y-2 text-center">
          <p className="font-semibold text-foreground">The backend is not reachable</p>
          <p className="text-sm text-muted-foreground">{apiErrorMessage(query.error)}</p>
          <p className="text-sm text-muted-foreground">
            Start the app with start-binance.bat or start-yahoo.bat, then reload this page.
          </p>
        </div>
      ) : (
        <Loading text="Connecting to the backend..." />
      )}
    </div>
  );
};
