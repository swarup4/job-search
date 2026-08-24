import { cn } from "@/util/cn";

/** Box sizes mirror the $ring-sizes map in style/globals.scss. */
const GEO = {
  sm: { box: 38, stroke: 3 },
  md: { box: 48, stroke: 3 },
  lg: { box: 62, stroke: 4 },
};

export function MatchScore({ value, size = "md" }) {
  const { box, stroke } = GEO[size] ?? GEO.md;
  const r = (box - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const strong = value >= 80;

  return (
    <div
      className={cn(
        "match-score",
        `match-score--${size}`,
        strong && "match-score--strong"
      )}
    >
      <svg width={box} height={box} aria-hidden>
        <circle
          className="match-score__track"
          cx={box / 2}
          cy={box / 2}
          r={r}
          strokeWidth={stroke}
        />
        <circle
          className="match-score__value"
          cx={box / 2}
          cy={box / 2}
          r={r}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - value / 100)}
        />
      </svg>
      <span className="match-score__label">
        {value}
        {size === "lg" ? <span className="match-score__pct">%</span> : null}
      </span>
    </div>
  );
}
