/** Official Coat of Arms of Kenya (not the flag). */
const COAT_OF_ARMS =
  "https://upload.wikimedia.org/wikipedia/commons/f/f6/Coat_of_arms_of_Kenya_%28Official%29.svg";

export function KenyaFlag({ className = "kenya-crest" }: { className?: string }) {
  return (
    <img
      className={className}
      src={COAT_OF_ARMS}
      alt="Coat of arms of Kenya"
      width={48}
      height={48}
      decoding="async"
    />
  );
}

/** Prefer this name in new code */
export function KenyaCrest({ className = "kenya-crest" }: { className?: string }) {
  return <KenyaFlag className={className} />;
}
