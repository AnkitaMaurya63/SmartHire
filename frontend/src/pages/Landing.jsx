import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, BadgeCheck, Compass, FileText, ListChecks, Lock, Mic, ShieldCheck, Sparkles, Workflow, Zap } from "lucide-react";
import { EASE, Float, HoverLift, Item, Reveal, Stagger, fadeUp, stagger } from "../lib/motion.jsx";
import CountUp from "../components/CountUp.jsx";
import { Bar, ScoreRing } from "../components/charts.jsx";

const FEATURES = [
  { icon: Workflow, title: "Ten agents, one workflow", text: "A LangGraph pipeline parses, matches, scores, finds gaps, predicts a category with a trained model and prepares interviews. Independent agents run in parallel." },
  { icon: ShieldCheck, title: "Fabrication guard", text: "A critic agent rejects any rewrite that adds numbers or technologies that are not in your resume, so you never claim anything untrue." },
  { icon: ListChecks, title: "Skill-evidence check", text: "See which skills are proven in a project or job and which are only listed. Interviewers will ask for proof of the second kind." },
  { icon: Compass, title: "Hybrid role matching", text: "Embeddings and FAISS vector search are blended with weighted skill coverage across 18 roles." },
  { icon: FileText, title: "Tailor to any job description", text: "Paste a JD. Lines marked must or mandatory become must-have skills, and your resume is scored against them." },
  { icon: Mic, title: "Interview coach", text: "Practice questions about your own projects and the skills the role needs, including what was your individual contribution." },
];

const STEPS = [
  ["Upload", "Drop a PDF resume and pick a role, or paste a job description."],
  ["Agents analyse", "Parser, matcher, scorer, gap analyst and coach work together."],
  ["Critic verifies", "Every AI rewrite is checked so nothing is invented."],
  ["Improve and practise", "Fix weak bullets, close skill gaps and rehearse answers."],
];

const FLOW = ["Parser", "Matcher", "Target", "Scorer · Gaps · Coach · ML", "Rewriter ⇄ Critic", "Reporter"];

function HeroVisual() {
  return (
    <motion.div className="hero-visual" initial={{ opacity: 0, scale: 0.95, y: 24 }} animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.9, ease: EASE, delay: 0.3 }}>
      <Float className="orb" y={18} duration={9} style={{ width: 220, height: 220, top: 10, right: 10, background: "#7c5cff" }} />
      <Float className="orb" y={14} duration={11} delay={1} style={{ width: 180, height: 180, bottom: 0, left: 0, background: "#22d3ee" }} />
      <Float y={8} duration={7}>
        <div className="mock" aria-label="Sample resume report">
          <div className="mock-head">
            <div className="mock-dots"><i /><i /><i /></div>
            <span className="badge">Sample report</span>
          </div>
          <div className="mock-score">
            <ScoreRing score={82} size={118} stroke={11} />
            <div className="mock-bars">
              {[["Keywords", 86], ["Impact", 71], ["Evidence", 64], ["GitHub", 80]].map(([l, v], i) => (
                <div key={l}><span><span>{l}</span><span>{v}</span></span><Bar value={v} delay={0.5 + i * 0.1} /></div>
              ))}
            </div>
          </div>
        </div>
      </Float>
      <Float className="float-chip" style={{ top: 28, left: 0 }} y={9} duration={5.5}><BadgeCheck size={16} /> Critic approved rewrite</Float>
      <Float className="float-chip" style={{ bottom: 70, right: -6 }} y={10} duration={6.5} delay={0.8}><Zap size={16} style={{ color: "var(--warn)" }} /> 7 skill gaps found</Float>
      <Float className="float-chip" style={{ bottom: 6, left: 28 }} y={8} duration={7} delay={1.4}><ShieldCheck size={16} /> No invented numbers</Float>
    </motion.div>
  );
}

export default function Landing() {
  return (
    <>
      <section className="container hero">
        <motion.div className="hero-copy" variants={stagger(0.11, 0.1)} initial="hidden" animate="show">
          <motion.span variants={fadeUp} className="eyebrow"><Sparkles size={14} /> Multi-agent resume intelligence</motion.span>
          <motion.h1 variants={fadeUp} className="display">
            Your resume, reviewed by a <span className="grad-text">team of AI agents</span>
          </motion.h1>
          <motion.p variants={fadeUp} className="lead">
            Upload your resume and get an honest ATS score, best-fit roles, skill gaps, safer rewrites and interview questions built from your own projects.
          </motion.p>
          <motion.div variants={fadeUp} className="cta-row">
            <HoverLift><Link to="/analyze" className="btn btn-primary btn-lg">Analyze my resume <ArrowRight size={18} /></Link></HoverLift>
            <HoverLift><a href="#how" className="btn btn-ghost btn-lg">See how it works</a></HoverLift>
          </motion.div>
          <motion.ul variants={fadeUp} className="trust">
            <li><Lock size={15} /> Never stored</li>
            <li><BadgeCheck size={15} /> Works without an API key</li>
            <li><Zap size={15} /> Results in seconds</li>
          </motion.ul>
        </motion.div>
        <HeroVisual />
      </section>

      <section className="container" aria-label="At a glance">
        <Reveal>
          <div className="stats">
            {[[10, "AI agents", ""], [18, "Target roles", ""], [99, "Skills tracked", ""], [6, "Scoring factors", ""]].map(([n, l, s]) => (
              <div className="stat" key={l}><b><CountUp to={n} suffix={s} /></b><span>{l}</span></div>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="container section" id="features">
        <Reveal className="section-head center">
          <span className="eyebrow-label">Features</span>
          <h2>Built to be honest, not flattering</h2>
          <p className="lead">Every feature exists to help you show real strengths and fix real gaps.</p>
        </Reveal>
        <div className="grid grid-3">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={(i % 3) * 0.08}>
              <motion.div className="card card-hover feature" whileHover={{ y: -6 }} transition={{ type: "spring", stiffness: 300, damping: 24 }}>
                <span className="f-icon"><f.icon size={22} /></span>
                <h3>{f.title}</h3>
                <p>{f.text}</p>
              </motion.div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="container section" id="how" style={{ paddingTop: 0 }}>
        <Reveal className="section-head center">
          <span className="eyebrow-label">How it works</span>
          <h2>From upload to action plan in four steps</h2>
        </Reveal>
        <Stagger className="steps" inView gap={0.12}>
          {STEPS.map(([t, d], i) => (
            <Item key={t} className="card step"><div className="step-n">{i + 1}</div><h3>{t}</h3><p>{d}</p></Item>
          ))}
        </Stagger>
        <Stagger className="flow-chips" inView gap={0.07}>
          {FLOW.map((f, i) => (
            <Item key={f} className="flow-chip-wrap" style={{ display: "contents" }}>
              <span className="chip">{f}</span>
              {i < FLOW.length - 1 && <ArrowRight size={14} className="arrow" />}
            </Item>
          ))}
        </Stagger>
      </section>

      <section className="container" style={{ paddingBottom: "clamp(56px, 9vw, 112px)" }}>
        <Reveal>
          <div className="cta-band">
            <h2>See what an interviewer will see</h2>
            <p className="lead">Free to try. Takes less than a minute. Includes a sample resume if you just want to look around.</p>
            <HoverLift><Link to="/analyze" className="btn btn-primary btn-lg">Analyze my resume <ArrowRight size={18} /></Link></HoverLift>
          </div>
        </Reveal>
      </section>
    </>
  );
}
