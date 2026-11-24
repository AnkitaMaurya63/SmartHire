import { useEffect, useRef } from "react";
import { animate, useInView, useReducedMotion } from "framer-motion";
import { EASE } from "../lib/motion.jsx";

/** Animated number. Writes straight to the DOM (no React re-render per frame) and
 *  jumps to the final value when the user prefers reduced motion. */
export default function CountUp({ to, duration = 1.3, decimals = 0, suffix = "", prefix = "" }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const fmt = (v) => `${prefix}${v.toFixed(decimals)}${suffix}`;

  useEffect(() => {
    if (!ref.current) return;
    if (!inView) return;
    if (reduce) { ref.current.textContent = fmt(to); return; }
    const controls = animate(0, to, { duration, ease: EASE, onUpdate: (v) => { if (ref.current) ref.current.textContent = fmt(v); } });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, to, reduce, duration]);

  return <span ref={ref}>{fmt(reduce ? to : 0)}</span>;
}
