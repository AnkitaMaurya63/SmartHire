import { useId } from "react";
import { motion } from "framer-motion";
import CountUp from "./CountUp.jsx";
import { EASE } from "../lib/motion.jsx";

export const toneOf = (v) => (v >= 75 ? "good" : v >= 50 ? "warn" : "bad");

/** Circular score gauge: the arc draws in and the number counts up. */
export function ScoreRing({ score, size = 150, stroke = 13 }) {
  const gid = "rg" + useId().replace(/:/g, "");
  const r = (size - stroke) / 2, c = 2 * Math.PI * r;
  return (
    <div className="ring" style={{ width: size, height: size }} role="img" aria-label={`Score ${score} out of 100`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#7c5cff" /><stop offset="1" stopColor="#22d3ee" /></linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,.09)" strokeWidth={stroke} />
        <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`url(#${gid})`} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - score / 100) }}
          transition={{ duration: 1.3, ease: EASE, delay: 0.2 }} />
      </svg>
      <div className="ring-num"><b><CountUp to={score} /></b><span>out of 100</span></div>
    </div>
  );
}

/** Progress bar that grows from the left (transform only, so it stays smooth on mobile). */
export function Bar({ value, tone, delay = 0 }) {
  return (
    <div className={`bar ${tone || toneOf(value)}`}>
      <motion.i initial={{ scaleX: 0 }} animate={{ scaleX: Math.max(0, Math.min(100, value)) / 100 }}
        transition={{ duration: 0.9, ease: EASE, delay }} />
    </div>
  );
}

export function Radar({ components }) {
  const keys = Object.keys(components), n = keys.length, R = 95, cx = 200, cy = 150;
  const pt = (i, v) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + R * v * Math.cos(a), cy + R * v * Math.sin(a)]; };
  const poly = keys.map((k, i) => pt(i, components[k].score / 100).join(",")).join(" ");
  return (
    <svg viewBox="0 0 400 310" width="100%" style={{ maxWidth: 440 }} role="img" aria-label="Score breakdown radar chart">
      {[0.25, 0.5, 0.75, 1].map((l) => (
        <polygon key={l} points={keys.map((_, i) => pt(i, l).join(",")).join(" ")} fill="none" stroke="rgba(255,255,255,.12)" />
      ))}
      {keys.map((k, i) => {
        const [x, y] = pt(i, 1), [lx, ly] = pt(i, 1.16);
        const anchor = lx < cx - 8 ? "end" : lx > cx + 8 ? "start" : "middle";
        return (
          <g key={k}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(255,255,255,.1)" />
            <text x={lx} y={ly} fill="#a0a9cb" fontSize="11" textAnchor={anchor} dominantBaseline="middle">{components[k].label}</text>
          </g>
        );
      })}
      <motion.g style={{ transformOrigin: `${cx}px ${cy}px` }} initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.9, ease: EASE, delay: 0.25 }}>
        <polygon points={poly} fill="rgba(124,92,255,.35)" stroke="#7c5cff" strokeWidth="2" strokeLinejoin="round" />
        {keys.map((k, i) => { const [x, y] = pt(i, components[k].score / 100); return <circle key={k} cx={x} cy={y} r="4" fill="#22d3ee" />; })}
      </motion.g>
    </svg>
  );
}
