import { Suspense, lazy, useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";
import Landing from "./pages/Landing.jsx";
import { EASE } from "./lib/motion.jsx";

// The analyzer (dashboard + charts) is code-split so the landing page loads fast.
const Analyze = lazy(() => import("./pages/Analyze.jsx"));

function Page({ children }) {
  return (
    <motion.main initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35, ease: EASE }}>
      {children}
    </motion.main>
  );
}

function ScrollManager() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (hash) {
      const t = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView(), 120);
      return () => clearTimeout(t);
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
}

export default function App() {
  const location = useLocation();
  return (
    <>
      <div className="bg-glow" aria-hidden="true" />
      <Navbar />
      <ScrollManager />
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Page><Landing /></Page>} />
          <Route path="/analyze" element={
            <Page>
              <Suspense fallback={<div className="container" style={{ minHeight: "60vh" }} />}><Analyze /></Suspense>
            </Page>} />
          <Route path="*" element={<Page><Landing /></Page>} />
        </Routes>
      </AnimatePresence>
      <Footer />
    </>
  );
}
