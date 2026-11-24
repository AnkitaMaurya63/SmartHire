import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Brain, Check, ClipboardList, Compass, FileText, Mic, PenLine, Puzzle, SearchCheck, Target } from "lucide-react";
import { EASE } from "../lib/motion.jsx";

const META = {
  parser_agent: { icon: FileText, name: "Parser" },
  matcher_agent: { icon: Compass, name: "Matcher" },
  target_agent: { icon: Target, name: "Target" },
  scorer_agent: { icon: BarChart3, name: "Scorer" },
  gap_agent: { icon: Puzzle, name: "Gaps" },
  interview_agent: { icon: Mic, name: "Coach" },
  classifier_agent: { icon: Brain, name: "ML Model" },
  rewriter_agent: { icon: PenLine, name: "Rewriter" },
  critic_agent: { icon: SearchCheck, name: "Critic" },
  reporter_agent: { icon: ClipboardList, name: "Reporter" },
};
const STAGES = [
  { ids: ["parser_agent"] }, { ids: ["matcher_agent"] }, { ids: ["target_agent"] },
  { ids: ["scorer_agent", "gap_agent", "interview_agent", "classifier_agent"], cap: "parallel" },
  { ids: ["rewriter_agent", "critic_agent"], cap: "retry loop" },
  { ids: ["reporter_agent"] },
];

export const initialAgents = { done: {}, retries: {} };

/** Fold one streamed agent event into the pipeline state. */
export function applyAgentEvent(prev, ev) {
  if (!ev.entry) return prev;
  const done = { ...prev.done }, retries = { ...prev.retries };
  if (done[ev.agent]) retries[ev.agent] = (retries[ev.agent] || 1) + 1;
  done[ev.agent] = ev.entry;
  if (ev.agent === "rewriter_agent") delete done.critic_agent; // a retry sends the critic back to work
  return { done, retries };
}

function runningSet(done) {
  const d = (id) => !!done[id];
  if (!d("parser_agent")) return new Set(["parser_agent"]);
  if (!d("matcher_agent")) return new Set(["matcher_agent"]);
  if (!d("target_agent")) return new Set(["target_agent"]);
  const par = ["scorer_agent", "gap_agent", "interview_agent", "classifier_agent"].filter((x) => !d(x));
  if (par.length) return new Set(par);
  if (!d("rewriter_agent")) return new Set(["rewriter_agent"]);
  if (!d("critic_agent")) return new Set(["critic_agent"]);
  if (!d("reporter_agent")) return new Set(["reporter_agent"]);
  return new Set();
}

function Node({ id, agents, running, index }) {
  const { icon: Icon, name } = META[id];
  const e = agents.done[id];
  const cls = e ? (e.status === "failed" ? "failed" : "done") : running.has(id) ? "running" : "";
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: EASE, delay: index * 0.05 }}>
      <div className={`node ${cls}`} title={e?.summary}>
        <div className="nm">
          <Icon size={15} /> {name}
          {agents.retries[id] > 0 && <span className="rt">×{agents.retries[id]}</span>}
          {e ? (
            <span className="ms">
              <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 18 }} style={{ display: "inline-block", verticalAlign: "middle", marginRight: 3 }}>
                <Check size={12} />
              </motion.span>
              {e.ms} ms
            </span>
          ) : null}
        </div>
        <div className="st">{e ? e.summary : running.has(id) ? "working..." : "waiting"}</div>
      </div>
    </motion.div>
  );
}

export default function Pipeline({ agents, note }) {
  const running = runningSet(agents.done);
  let i = 0;
  return (
    <div className="pipe-wrap">
      <div className="pipe-head"><h3>Agent workflow</h3><span className="muted small">{note}</span></div>
      <div className="flow">
        {STAGES.map((st, si) => (
          <div key={si} style={{ display: "contents" }}>
            {si > 0 && <ArrowRight size={16} className="arrow" />}
            <div className="stage">
              {st.cap && <div className="cap">{st.cap}</div>}
              {st.ids.map((id) => <Node key={id} id={id} agents={agents} running={running} index={i++} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
