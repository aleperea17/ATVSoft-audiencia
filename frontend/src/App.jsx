import { useCallback, useEffect, useState } from "react";
import { AuthError, getCalificados, getReels } from "./api";
import LeadCard from "./components/LeadCard.jsx";
import ReelList from "./components/ReelList.jsx";
import { LeadSkeletons, ReelSkeletons } from "./components/Skeletons.jsx";
import { formatPct, reelTitle } from "./format";
import styles from "./App.module.css";

const PAGE_SIZE = 50;

function readUrl() {
  const params = new URLSearchParams(window.location.search);
  const reel = Number(params.get("reel"));
  return {
    reelId: Number.isInteger(reel) && reel > 0 ? reel : null,
    vista: params.get("vista") === "todos" ? "todos" : "main",
  };
}

export default function App() {
  const initial = readUrl();
  const [status, setStatus] = useState("loading");
  const [reels, setReels] = useState([]);
  const [selectedId, setSelectedId] = useState(initial.reelId);
  const [vista, setVista] = useState(initial.vista);
  const [preview, setPreview] = useState({ status: "idle", items: [] });
  const [page, setPage] = useState({ status: "idle", items: [], total: 0, offset: 0 });

  const loadReels = useCallback(async () => {
    setStatus("loading");
    try {
      const data = await getReels();
      setReels(data);
      setSelectedId((current) => {
        if (current && data.some((reel) => reel.id === current)) return current;
        return data[0] ? data[0].id : null;
      });
      setStatus("ready");
    } catch (error) {
      setStatus(error instanceof AuthError ? "auth" : "error");
    }
  }, []);

  useEffect(() => {
    loadReels();
  }, [loadReels]);

  useEffect(() => {
    const onPop = () => {
      const next = readUrl();
      setVista(next.vista);
      if (next.reelId) setSelectedId(next.reelId);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    if (status !== "ready" || !selectedId || vista !== "main") return undefined;
    let cancelled = false;
    setPreview({ status: "loading", items: [] });
    getCalificados(selectedId, { limit: 5, offset: 0 })
      .then((data) => {
        if (!cancelled) setPreview({ status: "ready", items: data.items || [] });
      })
      .catch((error) => {
        if (cancelled) return;
        if (error instanceof AuthError) setStatus("auth");
        else setPreview({ status: "error", items: [] });
      });
    return () => {
      cancelled = true;
    };
  }, [status, selectedId, vista]);

  const loadPage = useCallback(
    async (offset) => {
      if (!selectedId) return;
      setPage((current) => ({ ...current, status: "loading", offset }));
      try {
        const data = await getCalificados(selectedId, { limit: PAGE_SIZE, offset });
        setPage({
          status: "ready",
          items: data.items || [],
          total: data.total || 0,
          offset,
        });
      } catch (error) {
        if (error instanceof AuthError) setStatus("auth");
        else setPage({ status: "error", items: [], total: 0, offset });
      }
    },
    [selectedId]
  );

  useEffect(() => {
    if (status !== "ready" || vista !== "todos" || !selectedId) return;
    loadPage(0);
  }, [status, vista, selectedId, loadPage]);

  function selectReel(id) {
    setSelectedId(id);
    const url = new URL(window.location.href);
    url.searchParams.set("reel", String(id));
    url.searchParams.delete("vista");
    window.history.replaceState({}, "", url);
  }

  function openAll(id) {
    setSelectedId(id);
    setVista("todos");
    const url = new URL(window.location.href);
    url.searchParams.set("reel", String(id));
    url.searchParams.set("vista", "todos");
    window.history.pushState({}, "", url);
  }

  function goBack() {
    if (window.history.length > 1 && readUrl().vista === "todos") {
      window.history.back();
      return;
    }
    setVista("main");
    const url = new URL(window.location.href);
    url.searchParams.delete("vista");
    window.history.replaceState({}, "", url);
  }

  if (status === "auth") {
    return (
      <main className={styles.gate}>
        <section className={styles.gateCard}>
          <p className={styles.brand}>
            <span className={styles.brandMark}>ATV</span> Audiencia
          </p>
          <h1 className={styles.gateTitle}>Necesitás la sesión del ecosistema</h1>
          <p className={styles.gateText}>
            Entrá a ATV con tu usuario. Esta pantalla lee la misma cookie de sesión.
          </p>
        </section>
      </main>
    );
  }

  const selected = reels.find((reel) => reel.id === selectedId) || null;

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <p className={styles.brand}>
          <span className={styles.brandMark}>ATV</span> Audiencia
        </p>
      </header>
      <main className={styles.shell}>
        {status === "error" ? (
          <div className={styles.errorBox}>
            <p>No se pudieron cargar los reels.</p>
            <button type="button" className={styles.back} onClick={loadReels}>
              Reintentar
            </button>
          </div>
        ) : null}

        {vista === "todos" ? (
          selected ? (
            <AllQualified
              reel={selected}
              page={page}
              onBack={goBack}
              onRetry={() => loadPage(page.offset || 0)}
              onPage={(offset) => loadPage(offset)}
            />
          ) : status === "loading" ? (
            <LeadSkeletons count={6} />
          ) : (
            <p className={styles.empty}>Ese reel no está en la lista.</p>
          )
        ) : (
          <div className={styles.layout}>
            <section className={styles.panel} aria-label="Reels">
              <header className={styles.panelHead}>Reels</header>
              <div className={styles.panelBody}>
                {status === "loading" ? <ReelSkeletons /> : null}
                {status === "ready" && reels.length === 0 ? (
                  <p className={styles.empty}>Todavía no hay reels. Se sincronizan solos cada 30 minutos.</p>
                ) : null}
                {status === "ready" && reels.length > 0 ? (
                  <ReelList reels={reels} selectedId={selectedId} onSelect={selectReel} onOpenAll={openAll} />
                ) : null}
              </div>
            </section>
            <section className={styles.panel} aria-label="Personas calificadas">
              <header className={styles.panelHead}>Personas calificadas</header>
              <div className={styles.panelBody}>
                {status === "loading" || preview.status === "loading" ? <LeadSkeletons /> : null}
                {status === "ready" && preview.status === "error" ? (
                  <p className={styles.empty}>No se pudo cargar el preview de este reel.</p>
                ) : null}
                {status === "ready" && preview.status === "ready" && preview.items.length === 0 ? (
                  <p className={styles.empty}>Nadie calificado en este reel todavía.</p>
                ) : null}
                {status === "ready" && preview.status === "ready"
                  ? preview.items.map((lead) => <LeadCard key={lead.ig_username} lead={lead} />)
                  : null}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

function AllQualified({ reel, page, onBack, onRetry, onPage }) {
  const total = page.status === "ready" ? page.total : reel.calificados;
  const pageIndex = Math.floor((page.offset || 0) / PAGE_SIZE);
  const pages = Math.max(1, Math.ceil((page.total || 0) / PAGE_SIZE));
  return (
    <section className={styles.all}>
      <button type="button" className={styles.back} onClick={onBack}>
        Volver
      </button>
      <header className={styles.allHead}>
        <div>
          <h1 className={styles.allTitle}>{reelTitle(reel.caption)}</h1>
          <p className={styles.meta}>
            {total} leads calificados
          </p>
        </div>
        <p className={styles.allPct}>{formatPct(reel.pct_calificado)}</p>
      </header>
      {page.status === "loading" ? <LeadSkeletons count={6} /> : null}
      {page.status === "error" ? (
        <div className={styles.errorBox}>
          <p>No se pudieron cargar los leads.</p>
          <button type="button" className={styles.back} onClick={onRetry}>
            Reintentar
          </button>
        </div>
      ) : null}
      {page.status === "ready" && page.items.length === 0 ? (
        <p className={styles.empty}>Nadie calificado en este reel todavía.</p>
      ) : null}
      {page.status === "ready" && page.items.length > 0 ? (
        <div className={styles.grid}>
          {page.items.map((lead) => (
            <LeadCard key={lead.ig_username} lead={lead} />
          ))}
        </div>
      ) : null}
      {page.status === "ready" && page.total > PAGE_SIZE ? (
        <div className={styles.pager}>
          <button
            type="button"
            className={styles.back}
            disabled={page.offset === 0}
            onClick={() => onPage(Math.max(0, page.offset - PAGE_SIZE))}
          >
            Anterior
          </button>
          <span className={styles.meta}>
            Página {pageIndex + 1} de {pages}
          </span>
          <button
            type="button"
            className={styles.back}
            disabled={page.offset + PAGE_SIZE >= page.total}
            onClick={() => onPage(page.offset + PAGE_SIZE)}
          >
            Siguiente
          </button>
        </div>
      ) : null}
    </section>
  );
}
