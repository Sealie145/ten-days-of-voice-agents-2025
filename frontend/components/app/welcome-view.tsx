import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-amber-700 mb-4 size-16"
    >
      {/* Minecraft-style blocky cube */}
      <rect x="16" y="8" width="32" height="32" fill="currentColor" opacity="0.3" />
      <path
        d="M16 8L32 0L48 8V24L32 32L16 24V8Z"
        fill="currentColor"
        opacity="0.6"
      />
      <path
        d="M48 8L64 16V40L48 48V24L48 8Z"
        fill="currentColor"
        opacity="0.4"
      />
      <path
        d="M16 24L0 32V56L16 48V24Z"
        fill="currentColor"
        opacity="0.5"
      />
      <rect x="20" y="44" width="24" height="16" fill="currentColor" opacity="0.7" />
      {/* Pickaxe */}
      <path
        d="M40 40L48 32M48 32L52 36M48 32L44 28"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium">
          ⛏️ Minecraft Voice Adventure
        </p>
        <p className="text-muted-foreground max-w-prose pt-2 text-sm leading-5">
          Your AI Game Master will guide you through a blocky survival adventure. Mine, craft, build, and explore - all with your voice!
        </p>
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5">
          Try saying: "I explore the cave" or "I want to craft a sword"
        </p>

        <Button variant="primary" size="lg" onClick={onStartCall} className="mt-6 w-64 font-mono">
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Need help getting set up? Check out the{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://docs.livekit.io/agents/start/voice-ai/"
            className="underline"
          >
            Voice AI quickstart
          </a>
          .
        </p>
      </div>
    </div>
  );
};
