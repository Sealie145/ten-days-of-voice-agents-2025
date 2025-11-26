export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'MobiKwik',
  pageTitle: 'MobiKwik SDR Agent - Voice AI Assistant',
  pageDescription: 'Connect with MobiKwik - India\'s leading digital financial services platform',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#D91E36',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#FF4D6A',
  startButtonText: 'Talk to MobiKwik SDR',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
