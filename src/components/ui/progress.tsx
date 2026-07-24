import * as ProgressPrimitive from "@radix-ui/react-progress";

interface ProgressProps {
  value: number;
  label: string;
}

export function Progress({ value, label }: ProgressProps) {
  const safeValue = Math.max(0, Math.min(value, 100));
  return (
    <ProgressPrimitive.Root
      className="progress"
      value={safeValue}
      aria-label={label}
    >
      <ProgressPrimitive.Indicator
        className="progress__indicator"
        style={{ transform: `translateX(-${100 - safeValue}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}
