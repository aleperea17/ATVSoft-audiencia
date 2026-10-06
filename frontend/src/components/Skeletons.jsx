import styles from "./Skeleton.module.css";

export function ReelSkeletons() {
  return (
    <div aria-hidden="true">
      {Array.from({ length: 6 }, (_, index) => (
        <div className={styles.row} key={index}>
          <div className={styles.stack}>
            <span className={styles.lineWide} />
            <span className={styles.bar} />
            <span className={styles.lineMid} />
          </div>
          <span className={styles.pct} />
        </div>
      ))}
    </div>
  );
}

export function LeadSkeletons({ count = 5 }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <div className={styles.card} key={index}>
          <span className={styles.avatar} />
          <div className={styles.stack}>
            <span className={styles.lineMid} />
            <span className={styles.lineWide} />
          </div>
        </div>
      ))}
    </div>
  );
}
