import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-pink-600 mb-4 size-16"
    >
      {/* Shopping bag */}
      <path
        d="M12 20L8 56H56L52 20H12Z"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M20 20V16C20 9.37258 25.3726 4 32 4C38.6274 4 44 9.37258 44 16V20"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Heart (fashion/love) */}
      <path
        d="M32 38L28 34C24 30 24 24 28 20C32 16 36 18 32 22C28 18 32 16 36 20C40 24 40 30 36 34L32 38Z"
        fill="currentColor"
        opacity="0.6"
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
          👗 Voice Shopping with Maya
        </p>
        <p className="text-muted-foreground max-w-prose pt-2 text-sm leading-5">
          Your AI fashion assistant. Browse trending brands, discover styles, and shop - all with your voice!
        </p>
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5">
          Try saying: "Show me men's t-shirts" or "I need a dress for a party"
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
