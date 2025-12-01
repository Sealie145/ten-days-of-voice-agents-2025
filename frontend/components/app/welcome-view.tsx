import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-purple-600 mb-4 size-16"
    >
      <path
        d="M32 8C24 8 18 14 18 22C18 26 20 30 24 32L20 56H28L30 40H34L36 56H44L40 32C44 30 46 26 46 22C46 14 40 8 32 8Z"
        fill="currentColor"
        opacity="0.3"
      />
      <circle cx="26" cy="20" r="3" fill="currentColor" />
      <circle cx="38" cy="20" r="3" fill="currentColor" />
      <path
        d="M24 28C24 28 28 32 32 32C36 32 40 28 40 28"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <path
        d="M16 18L12 14M48 18L52 14"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M8 28L4 28M56 28L60 28"
        stroke="currentColor"
        strokeWidth="3"
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
          🎭 Welcome to Improv Battle!
        </p>
        <p className="text-muted-foreground max-w-prose pt-2 text-sm leading-5">
          A voice-first improv game show where you perform short scenes and get real-time feedback from your AI host.
        </p>
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5">
          Say your name to start, then improvise through 3-5 rounds of creative scenarios!
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
