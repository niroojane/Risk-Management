import { createContext, useContext } from 'react';
import type { Profile } from '@/types/profile';

/** Filled by ProfileProvider once the backend's market profile is loaded */
export const ProfileContext = createContext<Profile | null>(null);

export const PROFILE_KEY = ['profile'];

export const useProfile = (): Profile => {
  const profile = useContext(ProfileContext);
  if (!profile) throw new Error('useProfile must be used inside ProfileProvider');
  return profile;
};

export const useIsMultiAsset = () => useProfile().name === 'multi_asset';
