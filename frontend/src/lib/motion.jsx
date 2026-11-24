import { motion } from "framer-motion";

// One easing curve everywhere keeps the whole UI feeling consistent.
export const EASE = [0.22, 1, 0.36, 1];

export const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } },
};

export const stagger = (gap = 0.1, start = 0.05) => ({
  hidden: {},
  show: { transition: { staggerChildren: gap, delayChildren: start } },
});

/** Scroll-triggered reveal: fades up once when it enters the viewport. */
export function Reveal({ children, delay = 0, y = 24, className, as = "div", style }) {
  const Tag = motion[as];
  return (
    <Tag className={className} style={style} initial={{ opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }} transition={{ duration: 0.65, ease: EASE, delay }}>
      {children}
    </Tag>
  );
}

/** Container that staggers its <Item> children (on mount, or when scrolled into view). */
export function Stagger({ children, className, gap = 0.08, inView = false, as = "div" }) {
  const Tag = motion[as];
  const props = inView
    ? { whileInView: "show", viewport: { once: true, margin: "-80px" } }
    : { animate: "show" };
  return (
    <Tag className={className} variants={stagger(gap)} initial="hidden" {...props}>
      {children}
    </Tag>
  );
}

export function Item({ children, className, as = "div", style }) {
  const Tag = motion[as];
  return <Tag className={className} style={style} variants={fadeUp}>{children}</Tag>;
}

/** Subtle button/card hover: small lift, tiny press feedback. Transform only (GPU friendly). */
export function HoverLift({ children, lift = 2, scale = 1.015, className, style }) {
  return (
    <motion.div className={className} style={{ display: "inline-block", ...style }}
      whileHover={{ y: -lift, scale }} whileTap={{ scale: 0.98 }} transition={{ type: "spring", stiffness: 380, damping: 26 }}>
      {children}
    </motion.div>
  );
}

/** Gentle looping float for decorative elements. */
export function Float({ children, y = 10, duration = 6, delay = 0, className, style }) {
  return (
    <motion.div className={className} style={style} animate={{ y: [0, -y, 0] }}
      transition={{ duration, delay, repeat: Infinity, ease: "easeInOut" }}>
      {children}
    </motion.div>
  );
}
