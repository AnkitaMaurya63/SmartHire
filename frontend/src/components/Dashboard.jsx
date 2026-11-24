import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BarChart3, Brain, Compass, Download, Mic, PenLine, Printer, Puzzle, Cpu } from "lucide-react";
import { EASE, HoverLift, Item, Stagger } from "../lib/motion.jsx";
import { Bar, Radar, ScoreRing, toneOf } from "./charts.jsx";
import { getJSON } from "../lib/api.js";

const chip = (t, cls = "") => <span key={t} className={`chip ${cls}`}>{t}</span>;
const TABS = [
  ["overview", "Overview", BarChart3], ["roles", "Roles", Compass], ["skills", "Skills", Puzzle],
  ["improve", "Improve", PenLine], ["interview", "Interview", Mic], ["ml", "ML model", Brain], ["trace", "Trace", Cpu],
];

/* ---------- panels ---------- */
function Overview({ r }) {
  const s = r.score, c = r.candidate;
  return (
    <Stagger className="stack" gap={0.09}>
      <Item className="grid grid-2">
        <div className="card">
          <div className="scorebox">
            <ScoreRing score={s.overall} />
            <div>
              <div className="grade">{s.grade}</div>
              <div className="muted small">Scored against: {r.target.title}</div>
              {r.target.jd_similarity != null && <div className="muted small">Semantic similarity to your JD: {r.target.jd_similarity}%</div>}
              <div className="chips" style={{ marginTop: 12 }}>
                {chip(c.name)} {chip(`${c.pages} page${c.pages > 1 ? "s" : ""}`)} {chip(`${c.words} words`)}
                {chip(c.links.github_profile ? "GitHub ✓" : "GitHub ✗", c.links.github_profile ? "good" : "bad")}
                {chip(`${c.links.repos.length} repo link${c.links.repos.length === 1 ? "" : "s"}`, c.links.repos.length >= 2 ? "good" : "warn")}
                {chip(c.links.linkedin ? "LinkedIn ✓" : "LinkedIn ✗", c.links.linkedin ? "good" : "warn")}
              </div>
            </div>
          </div>
          <div className="verdict">
            <span className="badge" style={{ marginBottom: 6 }}>{r.meta.summary_mode === "ai" ? "AI recruiter verdict" : "Summary"}</span>
            <div>{r.summary}</div>
          </div>
        </div>
        <div className="card" style={{ display: "grid", placeItems: "center" }}><Radar components={s.components} /></div>
      </Item>
      <Item className="grid grid-2">
        <div className="card">
          <h3>Score breakdown</h3>
          {Object.values(s.components).map((k, i) => (
            <div className="bar-row" key={k.label}>
              <div>{k.label} ({Math.round(k.weight * 100)}%)</div>
              <Bar value={k.score} delay={0.3 + i * 0.08} />
              <div className="muted">{k.score}</div>
            </div>
          ))}
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 6 }}>Top fixes</h3>
          {!s.issues.length && <div className="muted">No major issues found. Nice work.</div>}
          {s.issues.map((i, n) => (
            <div className="issue" key={n}><span className={`sev ${i.severity}`}>{i.severity}</span><div><b>{i.area}: </b>{i.text}</div></div>
          ))}
        </div>
      </Item>
    </Stagger>
  );
}

function Roles({ r, onRescore }) {
  return (
    <div>
      <p className="muted small" style={{ marginBottom: 14 }}>
        Domain-fit score = 55% weighted skill coverage + 45% semantic similarity ({r.meta.embeddings}, {r.meta.index} vector search).
      </p>
      <Stagger className="stack" gap={0.07}>
        {r.matches.map((m) => (
          <Item key={m.id}>
            <div className={`card role ${m.id === r.target.id ? "target" : ""}`}>
              <div className="rhead">
                <div>
                  <h3>{m.title}</h3>
                  <div className="muted small">{m.category}</div>
                  {m.id === r.target.id && <span className="badge" style={{ marginTop: 8 }}>Scored against this</span>}
                </div>
                <div className="rscore grad-text" title="Domain-fit score">{m.score}%<div className="muted small" style={{ fontSize: 11, fontWeight: 500 }}>domain fit</div></div>
              </div>
              <div className="mini">Skill coverage <Bar value={m.coverage} /> {m.coverage}%</div>
              <div className="mini">Semantic fit <Bar value={m.semantic} delay={0.1} /> {m.semantic}%</div>
              <div className="sub">You have</div>
              <div className="chips">{m.matched.slice(0, 12).map((s) => chip(s, "good"))}</div>
              {m.missing.length > 0 && (<><div className="sub">Missing</div><div className="chips">{m.missing.slice(0, 8).map((s) => chip(s, "bad"))}</div></>)}
              {m.id !== r.target.id && (
                <div style={{ marginTop: 14 }}><HoverLift><button className="btn btn-ghost btn-sm" onClick={() => onRescore(m.id)}>Score my resume against this role</button></HoverLift></div>
              )}
            </div>
          </Item>
        ))}
      </Stagger>
    </div>
  );
}

function Skills({ r }) {
  const proven = r.skills.filter((s) => s.demonstrated), listed = r.skills.filter((s) => !s.demonstrated);
  const miss = r.gaps.missing || [];
  return (
    <Stagger className="stack" gap={0.09}>
      <Item className="grid grid-2">
        <div className="card">
          <h3>Proven skills ({proven.length})</h3>
          <p className="muted small" style={{ margin: "4px 0 12px" }}>Shown in a project or job: the strongest kind of evidence.</p>
          <div className="chips">{proven.map((s) => chip(s.name, "good"))}</div>
        </div>
        <div className="card">
          <h3>Listed but unproven ({listed.length})</h3>
          <p className="muted small" style={{ margin: "4px 0 12px" }}>Only in the skills list. Add each to a project bullet or remove it, because interviewers will ask for proof.</p>
          <div className="chips">{listed.length ? listed.map((s) => chip(s.name, "warn")) : chip("None, nice!", "good")}</div>
        </div>
      </Item>
      <Item className="card">
        <h3 style={{ marginBottom: 8 }}>Missing for {r.target.title}</h3>
        {!miss.length ? <div className="muted">You cover every skill this role asks for.</div> : (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Skill</th><th>Priority</th><th>~Hours</th><th>How to learn it</th></tr></thead>
              <tbody>
                {miss.map((m) => (
                  <tr key={m.skill}>
                    <td><b>{m.skill}</b><div className="muted small">{m.category}</div></td>
                    <td><span className={`prio ${m.priority}`}>{m.priority}</span></td>
                    <td>{m.hours}</td><td>{m.tip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Item>
      {(r.gaps.roadmap || []).length > 0 && (
        <Item>
          <h3 style={{ margin: "8px 0 12px" }}>Learning roadmap</h3>
          <div className="road">
            {r.gaps.roadmap.map((b) => (
              <div className="card" key={b.label}>
                <h4>{b.label}</h4>
                <ul>{b.items.map((m) => <li key={m.skill}><b>{m.skill}</b> · {m.hours}h</li>)}</ul>
              </div>
            ))}
          </div>
        </Item>
      )}
    </Stagger>
  );
}

function CopyButton({ text }) {
  const [done, setDone] = useState(false);
  return (
    <button className="btn btn-ghost btn-sm copy" onClick={async () => { try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); } catch { /* clipboard unavailable */ } }}>
      {done ? "Copied ✓" : "Copy"}
    </button>
  );
}

function Improve({ r }) {
  const w = r.rewrites;
  if (w.mode === "none") return <div className="card">All your bullets already start with a strong verb and show a result. Nothing to rewrite.</div>;
  return (
    <div>
      {w.mode === "tips" ? (
        <div className="alert warn" style={{ marginBottom: 14 }}>
          {w.llm_error ? `The AI rewrite failed (${w.llm_error}), so rule-based tips are shown.` : "AI rewriting is off. Add a free Groq or Gemini key to .env to let the Rewriter and Critic agents draft improved bullets."}
        </div>
      ) : (
        <p className="muted small" style={{ marginBottom: 14 }}>
          Each rewrite is checked by the Critic: it must start with an action verb, stay concise, keep your facts and must not add numbers or technologies that are not already in your resume ({r.meta.rewrite_attempts} attempt(s) used).
        </p>
      )}
      <Stagger className="stack" gap={0.08}>
        {w.items.map((it, n) => (
          <Item key={n}>
            <div className="card">
              {it.project && <span className="badge" style={{ marginBottom: 8 }}>{it.project}</span>}
              <div className="before">{it.original}</div>
              <div className="chips" style={{ marginTop: 10 }}>{it.issues.map((i) => chip(i, "bad"))}</div>
              {w.mode === "llm" && it.suggestion ? (
                <div className={`after ${it.approved ? "" : "bad"}`}>
                  <CopyButton text={it.suggestion} />
                  <div style={{ paddingRight: 70 }}>{it.suggestion}</div>
                  <div className="muted small" style={{ marginTop: 6 }}>
                    {it.approved ? `✓ Approved by Critic after ${it.attempts} attempt(s)` : `✗ Not approved: ${it.notes.join(" ")}`}
                  </div>
                </div>
              ) : (
                <ul style={{ margin: "12px 0 0", paddingLeft: 18 }}>{(it.tips || []).map((t) => <li key={t}>{t}</li>)}</ul>
              )}
            </div>
          </Item>
        ))}
      </Stagger>
    </div>
  );
}

function Interview({ r }) {
  const iv = r.interview;
  return (
    <div>
      <p className="muted small" style={{ marginBottom: 14 }}>Questions built from your projects and the skills this role needs ({iv.mode}). Practise answering each in 60 seconds.</p>
      <Stagger className="stack" gap={0.05}>
        {iv.questions.map((q, i) => (
          <Item key={i}>
            <div className="card qa">
              <span className="chip">{q.topic}</span>{q.source === "ai" && <span className="ai-tag">AI</span>}
              <div className="q">{i + 1}. {q.q}</div>
              <div className="why">Why they ask: {q.why}</div>
            </div>
          </Item>
        ))}
      </Stagger>
    </div>
  );
}


const pct = (v) => (v == null ? "n/a" : `${(v * 100).toFixed(1)}%`);

function MLModel({ r }) {
  const [card, setCard] = useState(null);
  useEffect(() => { getJSON("/api/model-card").then(setCard).catch(() => setCard({})); }, []);
  const preds = r.ml?.predictions || [];
  const c = card?.classifier, ab = card?.ablation;
  const cvKey = c?.metrics && Object.keys(c.metrics).find((k) => k.endsWith("accuracy_mean"));
  return (
    <Stagger className="stack" gap={0.09}>
      <Item className="grid grid-2">
        <div className="card">
          <h3>Predicted job category</h3>
          <p className="muted small" style={{ margin: "4px 0 12px" }}>From a TF-IDF classifier trained on labelled resumes. Bars show the model's relative score across categories, not a probability of being correct.</p>
          {!r.ml?.available ? (
            <div className="alert warn">No trained model found. Run <code>python ml/train.py --data data/resumes.csv</code>, then restart the server.</div>
          ) : preds.map((p, i) => (
            <div className="bar-row" key={p.category}>
              <div>{p.category}</div><Bar value={(p.confidence / preds[0].confidence) * 100} delay={0.2 + i * 0.1} /><div className="muted">{p.confidence}%</div>
            </div>
          ))}
        </div>
        <div className="card">
          <h3>Model card</h3>
          {!c?.available ? <p className="muted small" style={{ marginTop: 8 }}>Training results appear here after you run <code>ml/train.py</code>.</p> : (
            <>
              <p className="muted small" style={{ margin: "4px 0 12px" }}>{c.best_model} · {c.train_size} train / {c.test_size} test resumes · {c.classes.length} categories</p>
              <div className="chips">
                <span className="chip good">Top-1: {pct(c.metrics.accuracy)}</span>
                <span className="chip good">Top-3: {pct(c.metrics.top3_accuracy)}</span>
                <span className="chip">Macro-F1: {c.metrics.macro_f1}</span>
                {cvKey && <span className="chip">{cvKey.split("_")[0].replace("cv", "")}-fold CV: {pct(c.metrics[cvKey])} ± {pct(c.metrics[cvKey.replace("mean", "std")])}</span>}
              </div>
              <ul className="muted small" style={{ margin: "12px 0 0", paddingLeft: 18 }}>{c.notes.map((n) => <li key={n}>{n}</li>)}</ul>
            </>
          )}
        </div>
      </Item>
      {ab && (
        <Item className="card">
          <h3>Matcher ablation</h3>
          <p className="muted small" style={{ margin: "4px 0 12px" }}>Which ranking method puts a correct role in the top results? {ab.resumes} unique labelled resumes · embeddings: {ab.embeddings}.</p>
          <div className="table-scroll">
            <table>
              <thead><tr><th>Method</th><th>Top-1</th><th>Top-3</th></tr></thead>
              <tbody>{Object.entries(ab.results).map(([k, v]) => <tr key={k}><td><b>{k}</b></td><td>{pct(v.top1)}</td><td>{pct(v.top3)}</td></tr>)}</tbody>
            </table>
          </div>
        </Item>
      )}
    </Stagger>
  );
}

function Trace({ r }) {
  const m = r.meta;
  return (
    <Stagger className="stack" gap={0.09}>
      <Item className="card">
        <div className="chips">
          {chip(`Total: ${(m.elapsed_ms / 1000).toFixed(2)} s`, "good")} {chip(`Embeddings: ${m.embeddings}`)} {chip(`Index: ${m.index}`)}
          {chip(`LLM: ${m.llm ? `${m.llm.provider} / ${m.llm.model}` : "off"}`, m.llm ? "good" : "warn")} {chip(`Rewrite attempts: ${m.rewrite_attempts}`)}
        </div>
      </Item>
      <Item className="card">
        <div className="table-scroll">
          <table>
            <thead><tr>{["#", "Agent", "Status", "Time", "What it did", "Tools"].map((t) => <th key={t}>{t}</th>)}</tr></thead>
            <tbody>
              {r.trace.map((t, i) => (
                <tr key={i}>
                  <td>{i + 1}</td><td><b>{t.label}</b></td>
                  <td><span className={`chip ${t.status === "done" ? "good" : "bad"}`}>{t.status}</span></td>
                  <td>{t.ms} ms</td><td>{t.summary}</td>
                  <td><div className="chips">{t.tools.map((x) => chip(x))}</div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Item>
    </Stagger>
  );
}

/* ---------- shell with animated tabs ---------- */
export default function Dashboard({ report, onRescore }) {
  const [tab, setTab] = useState("overview");
  const download = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    a.download = "smarthire-report.json"; document.body.append(a); a.click(); a.remove();
  };
  const panels = { overview: Overview, roles: Roles, skills: Skills, improve: Improve, interview: Interview, ml: MLModel, trace: Trace };
  const Panel = panels[tab];
  return (
    <div>
      <div className="tabs" role="tablist">
        {TABS.map(([id, label, Icon]) => (
          <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>
            <Icon size={16} /> {label}
            {tab === id && <motion.span layoutId="tab-line" className="tab-line" transition={{ type: "spring", stiffness: 420, damping: 36 }} />}
          </button>
        ))}
        <div className="tabs-actions">
          <button className="btn btn-ghost btn-sm" onClick={download}><Download size={15} /> JSON</button>
          <button className="btn btn-ghost btn-sm" onClick={() => window.print()}><Printer size={15} /> Print / PDF</button>
        </div>
      </div>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div key={tab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.22, ease: EASE }}>
          <Panel r={report} onRescore={onRescore} />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
