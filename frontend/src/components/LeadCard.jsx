import { AVATAR_LABEL, bioSnippet, initialOf } from "../format";
import VerifiedMark from "./VerifiedMark.jsx";
import styles from "./LeadCard.module.css";

export default function LeadCard({ lead }) {
  const username = lead.ig_username;
  const label = AVATAR_LABEL[lead.avatar] || lead.avatar;
  return (
    <article className={styles.card}>
      <span className={styles.avatar} aria-hidden="true">
        {initialOf(username)}
      </span>
      <div className={styles.body}>
        <div className={styles.userLine}>
          <a
            className={styles.user}
            href={`https://instagram.com/${encodeURIComponent(username)}`}
            target="_blank"
            rel="noreferrer"
          >
            @{username}
          </a>
          {lead.verificado === true ? <VerifiedMark /> : null}
        </div>
        <p className={styles.bio}>{bioSnippet(lead.bio)}</p>
        {label ? <span className={styles.chip}>{label}</span> : null}
      </div>
    </article>
  );
}
