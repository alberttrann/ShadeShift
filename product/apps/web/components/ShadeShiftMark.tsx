export function ShadeShiftMark({
  size = 42,
  compact = false,
}: {
  size?: number;
  compact?: boolean;
}) {
  return (
    <div
      className={`shadeShiftMark ${compact ? "compact" : ""}`}
      style={{ width: size, height: size }}
      aria-label="ShadeShift"
    >
      <svg viewBox="0 0 64 64" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="ssCool" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#59F0C0" />
            <stop offset="1" stopColor="#2B8DB8" />
          </linearGradient>
          <linearGradient id="ssHeat" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor="#F4C451" />
            <stop offset="1" stopColor="#F06D54" />
          </linearGradient>
          <clipPath id="ssRound">
            <rect x="4" y="4" width="56" height="56" rx="17" />
          </clipPath>
        </defs>

        <g clipPath="url(#ssRound)">
          <rect x="4" y="4" width="56" height="56" fill="#0B2432" />
          <rect x="4" y="4" width="28" height="28" fill="url(#ssCool)" />
          <rect x="32" y="4" width="28" height="28" fill="#10394A" />
          <rect x="4" y="32" width="28" height="28" fill="#145F65" />
          <rect x="32" y="32" width="28" height="28" fill="url(#ssHeat)" />

          <path
            d="M7 42 C20 31, 32 26, 57 16"
            stroke="rgba(255,255,255,.87)"
            strokeWidth="4.5"
            strokeLinecap="round"
            fill="none"
          />
          <circle cx="46" cy="17" r="6.5" fill="#FFE6A0" opacity=".95" />
        </g>

        <rect
          x="4.75"
          y="4.75"
          width="54.5"
          height="54.5"
          rx="16.25"
          fill="none"
          stroke="rgba(255,255,255,.18)"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
}
