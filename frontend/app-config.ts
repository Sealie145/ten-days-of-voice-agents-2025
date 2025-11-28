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
  companyName: 'Roshan Shop',
  pageTitle: 'Roshan Shop - Voice Grocery Ordering',
  pageDescription: 'Order groceries and food with your voice - powered by AI',

  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#10B981',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#34D399',
  startButtonText: 'Start Shopping',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
