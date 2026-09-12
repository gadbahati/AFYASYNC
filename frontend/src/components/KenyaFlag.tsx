export function KenyaFlag({ className = "kenya-flag" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 36 24"
      width="44"
      height="30"
      role="img"
      aria-label="Flag of Kenya"
    >
      <rect width="36" height="24" fill="#fff" />
      <rect y="0" width="36" height="6" fill="#000" />
      <rect y="6" width="36" height="1.5" fill="#fff" />
      <rect y="7.5" width="36" height="9" fill="#bb0000" />
      <rect y="16.5" width="36" height="1.5" fill="#fff" />
      <rect y="18" width="36" height="6" fill="#006600" />
      <ellipse cx="18" cy="12" rx="5.2" ry="7.2" fill="#fff" />
      <ellipse cx="18" cy="12" rx="3.6" ry="6" fill="#000" />
      <path d="M16.2 7.2 L19.8 12 L16.2 16.8 L15 15.4 L17.4 12 L15 8.6 Z" fill="#bb0000" />
      <path d="M19.8 7.2 L21 8.6 L18.6 12 L21 15.4 L19.8 16.8 L16.2 12 Z" fill="#bb0000" />
    </svg>
  );
}
