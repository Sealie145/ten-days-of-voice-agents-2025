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
  companyName: 'Myntra',
  pageTitle: 'Myntra Voice Shopping',
  pageDescription: 'Shop fashion with your voice - powered by AI',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#FF3F6C',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#FF5A7E',
  startButtonText: 'Start Shopping',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
