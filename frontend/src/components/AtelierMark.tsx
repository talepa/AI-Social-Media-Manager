/** Distinctive Atelier glyph — compass / lens motif (not Claude-style). */
export default function AtelierMark({
  size = 22,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
      className={`atelier-mark ${className}`.trim()}
    >
      <circle
        cx="12"
        cy="12"
        r="9.25"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        opacity="0.35"
      />
      <path
        d="M12 4.5v15M7.5 8.5 12 4.5 16.5 8.5M7.5 15.5 12 19.5 16.5 15.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="2.25" fill="currentColor" />
    </svg>
  );
}
