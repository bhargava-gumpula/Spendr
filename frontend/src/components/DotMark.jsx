export default function DotMark({ className }) {
  return (
    <svg className={className} viewBox="0 0 36 36" role="img" aria-label="Granted">
      <circle cx="13" cy="13" r="8" fill="var(--accent)" />
      <circle cx="24" cy="13" r="8" fill="var(--good)" />
      <circle cx="13" cy="24" r="8" fill="var(--warn)" />
      <circle cx="24" cy="24" r="8" fill="var(--bad)" />
    </svg>
  )
}
