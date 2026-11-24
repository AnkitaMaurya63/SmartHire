import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FileUp, Loader2 } from "lucide-react";
import { EASE, HoverLift, Item, Stagger } from "../lib/motion.jsx";
import { analyzeStream, getJSON } from "../lib/api.js";
import Pipeline, { applyAgentEvent, initialAgents } from "../components/Pipeline.jsx";
import Dashboard from "../components/Dashboard.jsx";

const smooth = () => (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");

export default function Analyze() {
  const [file, setFile] = useState(null);
  const [roles, setRoles] = useState([]);
  const [status, setStatus] = useState(null);
  const [roleId, setRoleId] = useState("");
  const [jd, setJd] = useState("");
  const [showJd, setShowJd] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | running | done
  const [error, setError] = useState("");
  const [agents, setAgents] = useState(initialAgents);
  const [report, setReport] = useState(null);
  const [over, setOver] = useState(false);
  const inputRef = useRef(null), pipeRef = useRef(null), resRef = useRef(null);

  useEffect(() => {
    getJSON("/api/status").then(setStatus).catch(() => setError("Cannot reach the SmartHire server. Is uvicorn running?"));
    getJSON("/api/roles").then(setRoles).catch(() => {});
  }, []);

  const groups = roles.reduce((acc, r) => { (acc[r.category] = acc[r.category] || []).push(r); return acc; }, {});

  async function loadSample() {
    try {
      const text = await (await fetch("/sample_resume.txt")).text();
      setFile(new File([text], "sample_resume.txt", { type: "text/plain" })); setError("");
    } catch { setError("Could not load the sample resume."); }
  }

  async function run(override) {
    const rid = typeof override === "string" ? override : roleId;
    if (typeof override === "string") setRoleId(override);
    setError(""); setPhase("running"); setReport(null); setAgents(initialAgents);
    setTimeout(() => pipeRef.current?.scrollIntoView({ behavior: smooth(), block: "start" }), 80);
    try {
      const rep = await analyzeStream({ file, roleId: rid, jd, onAgent: (ev) => setAgents((p) => applyAgentEvent(p, ev)) });
      setReport(rep); setPhase("done");
      setTimeout(() => resRef.current?.scrollIntoView({ behavior: smooth(), block: "start" }), 500);
    } catch (e) {
      setError(e.message); setPhase("idle");
      window.scrollTo({ top: 0, behavior: smooth() });
    }
  }

  const llm = status?.llm;
  return (
    <div className="container">
      <Stagger className="page-head" gap={0.08}>
        <Item as="h1" className="display" style={{ fontSize: "clamp(2rem, 4.6vw, 3rem)" }}>Analyze your resume</Item>
        <Item as="p" className="lead">Upload a PDF, choose the role you want, and watch the agents work.</Item>
        {status && (
          <Item className="pills">
            <span className="pill"><span className={`dot ${llm ? "on" : ""}`} />{llm ? <>LLM: <b>{llm.provider} · {llm.model}</b></> : "LLM off (add an API key for AI rewrites)"}</span>
            <span className="pill">Embeddings: <b>{status.embeddings}</b></span>
            <span className="pill">Vector index: <b>{status.index}</b></span>
          </Item>
        )}
      </Stagger>

      <motion.div className="card upload" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE, delay: 0.25 }}>
        <motion.button type="button" className={`drop ${over ? "over" : ""}`} whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) { setFile(f); setError(""); } }}>
          <span className="drop-ic"><FileUp size={26} /></span>
          {file ? (
            <div><div className="fname">{file.name}</div><span className="muted small">{(file.size / 1024).toFixed(0)} KB · click to change</span></div>
          ) : (
            <div><b>Drop your resume here</b><br /><span className="muted small">or click to browse (PDF or TXT, up to 5 MB)</span></div>
          )}
          <input ref={inputRef} type="file" accept=".pdf,.txt,.md" hidden onChange={(e) => { const f = e.target.files[0]; if (f) { setFile(f); setError(""); } }} />
        </motion.button>

        <div className="right-col">
          <div className="field">
            <label className="label" htmlFor="role">Target role</label>
            <select id="role" value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              <option value="">Auto: best-fit role for my resume</option>
              {Object.entries(groups).map(([cat, items]) => (
                <optgroup key={cat} label={cat}>{items.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}</optgroup>
              ))}
            </select>
          </div>
          <div>
            <button type="button" className="linkish" onClick={() => setShowJd((v) => !v)} aria-expanded={showJd}>{showJd ? "Hide job description" : "Or paste a job description"}</button>
            <AnimatePresence initial={false}>
              {showJd && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3, ease: EASE }} style={{ overflow: "hidden" }}>
                  <textarea style={{ marginTop: 10 }} value={jd} onChange={(e) => setJd(e.target.value)} aria-label="Job description"
                    placeholder="Paste the full job description. Lines marked must, mandatory or required count as must-have skills." />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <HoverLift style={{ display: "block" }}>
            <button className="btn btn-primary btn-lg btn-block" disabled={!file || phase === "running"} onClick={() => run()}>
              {phase === "running" ? <><Loader2 size={18} className="spin" /> Agents working...</> : "Analyze my resume"}
            </button>
          </HoverLift>
          <button type="button" className="linkish" onClick={loadSample}>No resume handy? Use a sample resume</button>
          <AnimatePresence>
            {error && <motion.div className="alert err" role="alert" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{error}</motion.div>}
          </AnimatePresence>
          <p className="muted small">Your file is analysed in memory and is never stored.</p>
        </div>
      </motion.div>

      <div ref={pipeRef} style={{ scrollMarginTop: 90 }}>
        <AnimatePresence>
          {phase !== "idle" && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
              <Pipeline agents={agents} note={phase === "running" ? "running live..." : report ? `finished in ${(report.meta.elapsed_ms / 1000).toFixed(1)} s` : ""} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div ref={resRef} style={{ scrollMarginTop: 90, paddingBottom: 72 }}>
        {report && phase === "done" && <Dashboard key={report.meta.elapsed_ms} report={report} onRescore={run} />}
      </div>
    </div>
  );
}
