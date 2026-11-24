export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-in">
        <span><b style={{ fontFamily: "var(--font-head)" }}>SmartHire</b> · Built with FastAPI, LangGraph and React</span>
        <span>Your resume is analysed in memory and is never stored.</span>
      </div>
    </footer>
  );
}
