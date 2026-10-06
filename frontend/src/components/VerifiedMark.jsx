import styles from "./VerifiedMark.module.css";

export default function VerifiedMark() {
  return (
    <svg className={styles.mark} viewBox="0 0 16 16" role="img" aria-label="Cuenta verificada">
      <circle cx="8" cy="8" r="8" fill="currentColor" />
      <path
        d="M4.6 8.2 6.8 10.4 11.4 5.7"
        fill="none"
        stroke="#ffffff"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
