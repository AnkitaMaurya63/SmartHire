import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Brain, ArrowRight } from "lucide-react";
import { EASE, HoverLift } from "../lib/motion.jsx";

export default function Navbar() {
  const { pathname } = useLocation();
  return (
    <motion.header className="nav" initial={{ y: -24, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.6, ease: EASE }}>
      <div className="container nav-in">
        <Link to="/" className="brand" aria-label="SmartHire home">
          <span className="brand-logo"><Brain size={19} /></span>
          <span className="brand-name">SmartHire</span>
        </Link>
        <nav className="nav-links" aria-label="Main">
          <Link className="link" to="/#features">Features</Link>
          <Link className="link" to="/#how">How it works</Link>
          {pathname !== "/analyze" && (
            <HoverLift>
              <Link to="/analyze" className="btn btn-primary btn-sm">Analyze resume <ArrowRight size={15} /></Link>
            </HoverLift>
          )}
        </nav>
      </div>
    </motion.header>
  );
}
