import React, { useRef, useEffect, useCallback, useReducer, useState } from "react";
import "./css/face_recherche.css";

const API = "http://localhost:8008";
const ROUTES = {
  health:      `${API}/api/face/health/`,
  reload:      `${API}/api/face/reload/`,
  identify:    `${API}/api/face/identify/`,
  identifyEtu: `${API}/api/face/identify/etudiants/`,
  identifyEns: `${API}/api/face/identify/enseignants/`,
};

const SCAN_INTERVAL = 2000;
const COOLDOWN_MS   = 4000;
const CONF_HIGH     = 80;
const CONF_MED      = 55;

const INIT = {
  apiStatus:     "loading",
  apiError:      "",
  facesLoaded:   0,
  breakdown:     { etudiants: 0, enseignants: 0, personnes: 0 },
  camActive:     false,
  liveMode:      false,
  scanning:      false,
  result:        null,
  trainStatus:   "idle",
  trainMessage:  "En attente...",
  trainProgress: 0,
  trainStats:    null,
};

function reducer(s, a) {
  switch (a.type) {
    case "API_OK":      return { ...s, apiStatus: "ok",    apiError: "", facesLoaded: a.h?.faces_loaded || 0, breakdown: a.h?.breakdown || s.breakdown };
    case "API_ERR":     return { ...s, apiStatus: "error", apiError: a.msg };
    case "CAM_ON":      return { ...s, camActive: true };
    case "CAM_OFF":     return { ...s, camActive: false, liveMode: false, scanning: false };
    case "LIVE_ON":     return { ...s, liveMode: true };
    case "LIVE_OFF":    return { ...s, liveMode: false };
    case "SCANNING":    return { ...s, scanning: a.v };
    case "RESULT":      return { ...s, scanning: false, result: a.data };
    case "TRAIN_START": return { ...s, trainStatus: "running", trainMessage: "Démarrage...", trainProgress: 5,   trainStats: null };
    case "TRAIN_PROG":  return { ...s, trainMessage: a.msg,    trainProgress: a.pct };
    case "TRAIN_DONE":  return { ...s, trainStatus: "done",    trainMessage: a.msg, trainProgress: 100, trainStats: a.stats };
    case "TRAIN_ERROR": return { ...s, trainStatus: "error",   trainMessage: a.msg, trainProgress: 0 };
    default:            return s;
  }
}

// ══════════════════════════════════════════
// HELPER PHOTO — construit l'URL Django
// ══════════════════════════════════════════
function buildPhotoUrl(raw) {
  if (!raw || typeof raw !== 'string') {
    console.warn("❌ buildPhotoUrl: raw invalid =", raw);
    return null;
  }
  
  console.log("🔧 buildPhotoUrl input:", raw);
  
  // Déjà URL complète
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    console.log("✅ URL complète, retour direct");
    return raw;
  }
  
  // Backslash Windows → slash
  let clean = raw.split("\\").join("/");
  
  // Si commence par /ai/media → ajouter le domain
  if (clean.startsWith("/ai/media/")) {
    const url = `${API}${clean}`;
    console.log("✅ /ai/media/ trouvé →", url);
    return url;
  }
  
  // Si commence juste par ai/media → ajouter /ai/media
  if (clean.startsWith("ai/media/")) {
    const url = `${API}/ai/media/${clean.replace(/^ai\/media\//, "")}`;
    console.log("✅ ai/media/ trouvé →", url);
    return url;
  }
  
  // Si commence par /media → ajouter le domain
  if (clean.startsWith("/media/")) {
    const url = `${API}${clean}`;
    console.log("✅ /media/ trouvé →", url);
    return url;
  }
  
  // Enlever leading slash si présent
  if (clean.startsWith("/")) clean = clean.substring(1);
  
  // Par défaut: supposer que c'est un chemin relative à /ai/media/
  const url = `${API}/ai/media/${clean}`;
  console.log("✅ Chemin relativo →", url);
  return url;
}

const cc = (v) => v >= CONF_HIGH ? "#10b981" : v >= CONF_MED ? "#f59e0b" : "#ef4444";

function Spinner({ size = 14 }) {
  return <span className="fr-spinner" style={{ width: size, height: size }} />;
}

function TypeBadge({ type }) {
  const map = {
    etudiant:   { cls: "badge-etu",  label: "🎓 Étudiant"   },
    enseignant: { cls: "badge-ens",  label: "👨‍🏫 Enseignant" },
    personne:   { cls: "badge-pers", label: "👤 Personne"    },
  };
  const c = map[type] || map.personne;
  return <span className={`type-badge ${c.cls}`}>{c.label}</span>;
}

// ══════════════════════════════════════════
// AVATAR — photo ou initiales
// ══════════════════════════════════════════
function Avatar({ photoRaw, initial }) {
  const url = buildPhotoUrl(photoRaw);

  if (url) {
    return (
      <img 
        className="avatar-img" 
        src={url} 
        alt=""
      />
    );
  }
  return <div className="avatar-mini">{initial}</div>;
}

function ConfBar({ value }) {
  const color = cc(value || 0);
  return (
    <div className="conf-bar-container">
      <div className="conf-bar-header">
        <span className="conf-bar-label">Fiabilité de correspondance</span>
        <span className="conf-bar-value" style={{ color }}>{Math.round(value || 0)}%</span>
      </div>
      <div className="conf-bar-track">
        <div className="conf-bar-fill" style={{ width: `${value || 0}%`, background: color }} />
      </div>
    </div>
  );
}

function InfoCard({ icon, label, value }) {
  if (!value) return null;
  return (
    <div className="info-card">
      <span className="info-card-label">{icon} {label}</span>
      <span className="info-card-value">{value}</span>
    </div>
  );
}

function FinanceBlock({ title, icon, rows }) {
  if (!rows.some(([, v]) => v != null)) return null;
  return (
    <div className="finance-block">
      <div className="finance-title">{icon} {title}</div>
      {rows.map(([lbl, val]) => val != null && (
        <div key={lbl} className="finance-row">
          <span className="finance-label">{lbl}</span>
          <span className="finance-val">
            {typeof val === "number" ? `${val.toLocaleString()} DA` : val}
          </span>
        </div>
      ))}
    </div>
  );
}

function TrainBanner({ status, message, progress, stats, onRetry }) {
  const cls   = { idle: "train-banner train-idle", running: "train-banner train-running", done: "train-banner train-done", error: "train-banner train-error" }[status] || "train-banner train-idle";
  const icon  = { idle: "⏳", running: "🔄", done: "✅", error: "❌" }[status];
  const title = { idle: "Rechargement en attente", running: "Rechargement en cours...", done: "Modèle prêt", error: "Rechargement échoué" }[status];
  return (
    <div className={cls}>
      <div className="train-top">
        <div className="train-left">
          <span className="train-icon">{icon}</span>
          <div>
            <p className="train-title">{title}</p>
            <p className="train-msg">{message}</p>
          </div>
        </div>
        {status === "done" && stats && (
          <div className="train-stats">
            {[["Total", stats.faces_loaded || stats.total], ["Étudiants", stats.breakdown?.etudiants], ["Enseignants", stats.breakdown?.enseignants], ["Personnes", stats.breakdown?.personnes]].map(([label, val]) => (
              <div key={label} className="train-stat-item">
                <p className="train-stat-val">{val ?? 0}</p>
                <p className="train-stat-label">{label}</p>
              </div>
            ))}
          </div>
        )}
        {status === "error" && (
          <button className="train-retry-btn" onClick={onRetry}>Réessayer</button>
        )}
      </div>
      {status === "running" && (
        <div className="train-progress-wrap">
          <div className="train-progress-meta">
            <span>{message}</span><span>{progress}%</span>
          </div>
          <div className="train-progress-track">
            <div className="train-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

export default function FaceRecognitionPage() {
  const [s, dispatch]               = useReducer(reducer, INIT);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [typeFiltre, setTypeFiltre] = useState("tous");
  const [tolerance, setTolerance]   = useState(0.90);  // 🎯 Tolérance de reconnaissance (augmentée)
  const [activeTab, setActiveTab]   = useState("personnel"); // 📑 Onglet actif : personnel ou financier

  const videoRef  = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const liveRef   = useRef(null);
  const lastOkRef = useRef(0);
  const progRef   = useRef(null);

  const apiFetch = useCallback(async (url, opts = {}, ms = 10000) => {
    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), ms);
    try {
      const r = await fetch(url, { ...opts, signal: ctrl.signal });
      clearTimeout(tid); return r;
    } catch (e) { clearTimeout(tid); throw e; }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const r = await apiFetch(ROUTES.health, {}, 5000);
      if (!r.ok) { dispatch({ type: "API_ERR", msg: `HTTP ${r.status}` }); return; }
      const h = await r.json();
      if (h.success || h.faces_loaded !== undefined) dispatch({ type: "API_OK", h });
      else dispatch({ type: "API_ERR", msg: h.error || "Erreur" });
    } catch (e) {
      dispatch({ type: "API_ERR", msg: e.name === "AbortError" ? "Timeout" : "Connexion refusée" });
    }
  }, [apiFetch]);

  const launchReload = useCallback(async () => {
    dispatch({ type: "TRAIN_START" });
    const steps = [[15,"Lecture des JSON..."],[35,"Chargement des images..."],[60,"Encodage des visages (dlib)..."],[80,"Calcul des descripteurs HOG..."],[90,"Finalisation..."]];
    let stepIdx = 0;
    progRef.current = setInterval(() => {
      if (stepIdx < steps.length) {
        const [pct, msg] = steps[stepIdx++];
        dispatch({ type: "TRAIN_PROG", msg, pct });
      }
    }, 800);
    try {
      const r    = await apiFetch(ROUTES.reload, { method: "POST" }, 60000);
      clearInterval(progRef.current);
      if (!r.ok) { dispatch({ type: "TRAIN_ERROR", msg: `Erreur HTTP ${r.status}` }); return; }
      const data = await r.json();
      if (data.success || data.faces_loaded > 0) {
        dispatch({ type: "TRAIN_DONE", msg: data.message || `${data.faces_loaded} visage(s) chargé(s)`, stats: data });
        checkHealth();
      } else {
        dispatch({ type: "TRAIN_ERROR", msg: data.message || "Aucun visage chargé" });
      }
    } catch (e) {
      clearInterval(progRef.current);
      dispatch({ type: "TRAIN_ERROR", msg: e.name === "AbortError" ? "Timeout (60s)" : e.message });
    }
  }, [apiFetch, checkHealth]);

  useEffect(() => {
    checkHealth();
    const iv = setInterval(checkHealth, 15000);
    launchReload();
    return () => { clearInterval(iv); clearInterval(progRef.current); };
  }, [checkHealth, launchReload]);

  const startCam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      });
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play().catch(() => {}); }
      dispatch({ type: "CAM_ON" });
    } catch (e) { alert("Webcam : " + e.message); }
  };

  const stopCam = () => {
    clearInterval(liveRef.current); liveRef.current = null;
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    dispatch({ type: "CAM_OFF" });
    dispatch({ type: "RESULT", data: null });
  };

  const capture = useCallback(() => {
    const v = videoRef.current, c = canvasRef.current;
    if (!v || !c || !v.videoWidth) return null;
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0);
    return c.toDataURL("image/jpeg", 0.85);
  }, []);

  const recognize = useCallback(async (auto = false) => {
    if (s.scanning) return;
    const b64 = capture();
    if (!b64) return;
    dispatch({ type: "SCANNING", v: true });
    const url = typeFiltre === "etudiant"   ? ROUTES.identifyEtu
              : typeFiltre === "enseignant" ? ROUTES.identifyEns
              : ROUTES.identify;
    try {
      const r = await apiFetch(url, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ image: b64, tolerance }),
      }, 15000);
      const d = await r.json();
      if (!r.ok) {
        dispatch({ type: "RESULT", data: { identified: false, error: d.error || `HTTP ${r.status}` } });
        return;
      }
      const personne = d.personne || null;
      const matches  = d.matches  || (personne ? [personne] : []);
      const found    = matches.find(m => m.identified)
                    || matches.find(m => m.nom || m.prenom || m.nom_complet || m.name)
                    || (personne?.nom || personne?.prenom ? personne : null)
                    || null;

      console.log("🔍 Found object complet:", found);
      console.log("📋 Tous les champs disponibles:", Object.keys(found || {}));

      const result = found ? {
        identified:    true,
        id:            found.id,
        type:          found.type           || "",
        nom:           found.nom            || "",
        prenom:        found.prenom         || "",
        nom_complet:   found.nom_complet    || found.name || `${found.prenom || ""} ${found.nom || ""}`.trim(),
        email:         found.email          || "",
        telephone:     found.telephone      || "",
        date_naissance:found.date_naissance || "",
        lieu_naissance:found.lieu_naissance || "",
        classe:        found.classe         || "",
        niveau:        found.niveau         || "",
        niveau_etude:  found.niveau_etude   || "",
        matiere:       found.matiere        || "",
        date_creation: found.date_creation  || "",
        photoRaw:      found.photo || found.image_file || found.image || found.photo_url || found.photo_path || "",
        confidence:    found.confidence || 0,
        assurance:     found.assurance  || null,
        paiements:     found.paiements  || null,
        debug:         d.debug,
      } : {
        identified: false,
        confidence: matches[0]?.confidence || d.confidence || 0,
        error:      d.message || d.debug?.message || "Non identifié",
        debug:      d.debug,
      };
      
      console.log("✅ Result photoRaw:", result.photoRaw);
      dispatch({ type: "RESULT", data: result });
      if (found?.identified) lastOkRef.current = Date.now();
    } catch (e) {
      dispatch({ type: "RESULT", data: { identified: false, error: e.name === "AbortError" ? "Timeout" : e.message } });
    }
  }, [s.scanning, capture, apiFetch, typeFiltre, tolerance]);

  const startLive = useCallback(() => {
    if (liveRef.current) return;
    dispatch({ type: "LIVE_ON" });
    liveRef.current = setInterval(() => {
      if (Date.now() - lastOkRef.current < COOLDOWN_MS) return;
      recognize(true);
    }, SCAN_INTERVAL);
  }, [recognize]);

  const stopLive = () => {
    clearInterval(liveRef.current); liveRef.current = null;
    dispatch({ type: "LIVE_OFF" });
  };

  useEffect(() => () => {
    clearInterval(liveRef.current); liveRef.current = null;
    clearInterval(progRef.current); progRef.current = null;
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
  }, []);

  const r          = s.result || {};
  const identified = r.identified;
  const canScan    = s.camActive && !s.scanning && s.apiStatus === "ok" && s.trainStatus !== "running";
  const fullName   = r.nom_complet || r.name || (r.prenom || r.nom ? `${r.prenom || ""} ${r.nom || ""}`.trim() : "") || "";
  const initial    = fullName.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) || "?";

  const handleRetour = () => {
    stopLive();
    stopCam();
    dispatch({ type: "RESULT", data: null });
    window.history.back();
  };
  return (
    <div className="face-page" data-theme={isDarkMode ? "dark" : "light"}>

      <header>
        <div className="header-left">
          <div className="logo-box">🧠</div>
          <div>
            <h1>FaceID — Reconnaissance Faciale</h1>
            <div className="subtitle">dlib · Django · Port 8008</div>
          </div>
        </div>
        <div className="header-right">
          {s.apiStatus === "ok" && (
            <div className="stats-breakdown">
              <span>🎓 {s.breakdown.etudiants}</span>
              <span>👨‍🏫 {s.breakdown.enseignants}</span>
              <span>👨‍💼 {s.breakdown.personnes}</span>
              <span>📦 {s.facesLoaded}</span>
            </div>
          )}
          <div className="api-badge">
            <div className={`dot ${s.apiStatus}`} />
            <span>
              {s.apiStatus === "ok"      ? "En ligne"     :
               s.apiStatus === "loading" ? "Connexion..." : "Hors ligne"}
            </span>
          </div>
          <button className="theme-btn" onClick={() => setIsDarkMode(!isDarkMode)}>
            {isDarkMode ? "☀️ Mode Clair" : "🌙 Mode Sombre"}
          </button>
        </div>
      </header>

      <div className="face-layout">

        <div className="train-section">
          <TrainBanner status={s.trainStatus} message={s.trainMessage} progress={s.trainProgress} stats={s.trainStats} onRetry={launchReload} />
        </div>

        <div className="filter-bar">
          <span className="filter-label">Filtrer :</span>
          {[
            { val: "tous",       label: "Tous"           },
            { val: "etudiant",   label: "🎓 Étudiants"   },
            { val: "enseignant", label: "👨‍🏫 Enseignants" },
            { val: "personne",   label: "👤 Personnes"    },
          ].map(t => (
            <button key={t.val} className={`filter-btn ${typeFiltre === t.val ? "filter-active" : ""}`} onClick={() => setTypeFiltre(t.val)}>
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ padding: "12px 16px", background: "rgba(255,255,255,0.05)", borderRadius: "8px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <label style={{ fontSize: "12px", fontWeight: "600", whiteSpace: "nowrap", color: "#999" }}>
            🎯 Tolérance de ressemblance:
          </label>
          <input 
            type="range" 
            min="0.40" 
            max="0.99" 
            step="0.01" 
            value={tolerance}
            onChange={(e) => setTolerance(parseFloat(e.target.value))}
            style={{ flex: 1, minWidth: "150px", cursor: "pointer" }}
          />
          <span style={{ fontSize: "14px", fontWeight: "700", color: tolerance > 0.85 ? "#10b981" : tolerance > 0.70 ? "#f59e0b" : "#ef4444", minWidth: "60px", textAlign: "right" }}>
            {(tolerance * 100).toFixed(0)}%
          </span>
        </div>

        <div className="main-grid">

          {/* CAMÉRA */}
          <div className="camera-card">
            <div className="camera-card-header">📷 Flux Vidéo Actif</div>
            <div className="camera-frame">
              <video ref={videoRef} autoPlay playsInline muted className={s.camActive ? "cam-active" : ""} />
              <canvas ref={canvasRef} />
              {!s.camActive && (
                <div className="cam-placeholder">
                  <div className="icon">📷</div>
                  <div>Caméra inactive</div>
                </div>
              )}
              {s.camActive && (
                <>
                  <div className="corner corner-tl" />
                  <div className="corner corner-tr" />
                  <div className="corner corner-bl" />
                  <div className="corner corner-br" />
                </>
              )}
              {s.liveMode  && <div className="overlay-status">🔴 LIVE MODE</div>}
              {s.scanning  && <div className="overlay-status scanning">⚡ ANALYSE EN COURS</div>}
              {identified && !s.scanning && (
                <div className="overlay-name overlay-ok" style={{ borderTop: `3px solid ${cc(r.confidence)}` }}>
                  ✓ {fullName} ({Math.round(r.confidence)}%)
                </div>
              )}
              {s.result && !identified && !s.scanning && (
                <div className="overlay-name overlay-fail">❌ Individu non identifié</div>
              )}
            </div>
            <div className="button-group">
              {!s.camActive ? (
                <button className="btn-action" onClick={startCam}>▶ Démarrer la caméra</button>
              ) : (
                <>
                  <button className="btn-action" onClick={() => recognize(false)} disabled={!canScan}>
                    {s.scanning ? <><Spinner /> Analyse...</> : "📸 Reconnaître"}
                  </button>
                  <button className="btn-action btn-live" onClick={s.liveMode ? stopLive : startLive} disabled={!canScan && !s.liveMode}>
                    {s.liveMode ? "⏹ Arrêter Live" : "🔄 Mode Continu"}
                  </button>
                  <button className="btn-action btn-danger" onClick={stopCam}>✕ Fermer</button>
                </>
              )}
            </div>
          </div>

          {/* RÉSULTATS */}
          <div className="results-card">
            <div className="results-card-header">
              <span>🎯 Résultats d'analyse</span>
              {identified && !s.scanning && (
                <div className="tab-buttons">
                  <button 
                    className={`tab-btn ${activeTab === "personnel" ? "tab-active" : ""}`}
                    onClick={() => setActiveTab("personnel")}
                  >
                    👤 Personnel
                  </button>
                  <button 
                    className={`tab-btn ${activeTab === "financier" ? "tab-active" : ""}`}
                    onClick={() => setActiveTab("financier")}
                  >
                    💰 Financier
                  </button>
                </div>
              )}
              {r.debug?.inference_ms && <span className="infer-ms">{r.debug.inference_ms}ms</span>}
            </div>
            <div className="results-card-body">

              {s.trainStatus === "running" && (
                <div className="state-empty">⏳ Chargement des visages...<br /><small>Patientez quelques instants.</small></div>
              )}
              {!s.result && !s.scanning && s.trainStatus !== "running" && (
                <div className="state-empty">En attente d'acquisition.<br />Activez la caméra et effectuez une reconnaissance.</div>
              )}
              {s.scanning && (
                <div className="state-scanning"><Spinner size={18} /> Extraction des descripteurs HOG & calcul des distances...</div>
              )}

              {identified && !s.scanning && (
                <div className="result-identified">
                  <div className="identity-row">
                    <Avatar photoRaw={r.photoRaw} initial={initial} />
                    <strong className="identity-name">{fullName}</strong>
                    <TypeBadge type={r.type} />
                  </div>
                  
                  {activeTab === "personnel" && (
                    <>
                      <ConfBar value={r.confidence} />
                      <div className="info-cards">
                        <InfoCard icon="📧" label="Email"     value={r.email} />
                        <InfoCard icon="📱" label="Téléphone" value={r.telephone} />
                        <InfoCard icon="🎂" label="Naissance" value={r.date_naissance} />
                        <InfoCard icon="📍" label="Lieu"      value={r.lieu_naissance} />
                        <InfoCard icon="🏫" label="Classe"    value={r.classe} />
                        <InfoCard icon="📚" label="Niveau"    value={r.niveau_etude || r.niveau} />
                        <InfoCard icon="✏️" label="Matière"   value={r.matiere} />
                        <InfoCard icon="📅" label="Depuis"    value={r.date_creation} />
                        <InfoCard icon="🆔" label="ID"        value={r.id ? String(r.id) : null} />
                      </div>
                    </>
                  )}
                  
                  {activeTab === "financier" && (
                    <>
                      {r.type === "etudiant" && (
                        <>
                          {r.assurance && (
                            <FinanceBlock title="Couverture Assurance" icon="🛡️" rows={[
                              ["Total",  r.assurance.montant_total],
                              ["Payé",   r.assurance.montant_paye],
                              ["Reste",  r.assurance.montant_restant],
                              ["Statut", r.assurance.statut],
                            ]} />
                          )}
                          {!r.assurance && (
                            <div className="state-empty">Aucune information d'assurance disponible.</div>
                          )}
                        </>
                      )}
                      
                      {r.type === "enseignant" && (
                        <>
                          {r.assurance && (
                            <FinanceBlock title="Couverture Assurance" icon="🛡️" rows={[
                              ["Total",  r.assurance.montant_total],
                              ["Payé",   r.assurance.montant_paye],
                              ["Reste",  r.assurance.montant_restant],
                              ["Statut", r.assurance.statut],
                            ]} />
                          )}
                          {r.paiements && (
                            <FinanceBlock title="Suivi Émoluments" icon="💵" rows={[
                              ["Prévu", r.paiements.salaire_prevu],
                              ["Versé", r.paiements.total_paye],
                              ["Reste", r.paiements.salaire_restant],
                            ]} />
                          )}
                          {!r.assurance && !r.paiements && (
                            <div className="state-empty">Aucune information financière disponible.</div>
                          )}
                        </>
                      )}
                      
                      {r.type !== "etudiant" && r.type !== "enseignant" && (
                        <div className="state-empty">Aucune information financière disponible pour ce type de personne.</div>
                      )}
                    </>
                  )}
                </div>
              )}

              {s.result && !identified && !s.scanning && (
                <div className="result-fail">
                  <strong>Alerte :</strong> Aucun profil ne correspond (seuil dlib : 0.70).
                  {r.error && <p className="fail-detail">{r.error}</p>}
                </div>
              )}
            </div>
          </div>
          <button type="button" className="btn-back" onClick={handleRetour}>
            ↩ Retour
          </button>
        </div>
      </div>
    </div>
  );
}