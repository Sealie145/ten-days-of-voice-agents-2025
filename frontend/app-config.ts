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
  companyName: 'Minecraft Adventure',
  pageTitle: 'Minecraft Voice Game Master',
  pageDescription: 'Embark on a voice-controlled Minecraft adventure with your AI Game Master',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#8B4513',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#A0522D',
  startButtonText: 'Start Adventure',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
