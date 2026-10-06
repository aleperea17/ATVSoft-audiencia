import { formatPct, reelTitle } from "../format";
import styles from "./ReelList.module.css";

export default function ReelList({ reels, selectedId, onSelect, onOpenAll }) {
  return (
    <div className={styles.list}>
      {reels.map((reel) => {
        const selected = reel.id === selectedId;
        const pct = Math.max(0, Math.min(100, Number(reel.pct_calificado) || 0));
        const pctLabel = formatPct(reel.pct_calificado);
        return (
          <div key={reel.id} className={selected ? `${styles.row} ${styles.selected}` : styles.row}>
            <button
              type="button"
              className={styles.selectBtn}
              aria-pressed={selected}
              onClick={() => onSelect(reel.id)}
            >
              <span className={styles.title}>{reelTitle(reel.caption)}</span>
              <span
                className={styles.track}
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(pct)}
                aria-label="Porcentaje de calificados"
              >
                <span className={styles.fill} style={{ width: `${pct}%` }} />
              </span>
              <span className={styles.meta}>
                {reel.calificados} calificados de {reel.total_interacciones} que interactuaron
              </span>
            </button>
            <button type="button" className={styles.pctBtn} onClick={() => onOpenAll(reel.id)}>
              <span className={styles.pct}>{pctLabel}</span>
              <span className={styles.ver}>Ver todos</span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
