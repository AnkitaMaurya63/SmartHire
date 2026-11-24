export async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Request failed (${r.status})`);
  return r.json();
}

/** Upload a resume and read the NDJSON stream. Calls onAgent(event) as each agent finishes,
 *  resolves with the final report. */
export async function analyzeStream({ file, roleId, jd, onAgent }) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("role_id", roleId || "");
  fd.append("jd_text", jd || "");
  const resp = await fetch("/api/analyze", { method: "POST", body: fd });
  if (!resp.ok) {
    let msg = `Request failed (${resp.status})`;
    try { msg = (await resp.json()).detail || msg; } catch { /* keep default */ }
    throw new Error(msg);
  }
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "", report = null;
  const handle = (line) => {
    if (!line.trim()) return;
    const ev = JSON.parse(line);
    if (ev.type === "agent") onAgent(ev);
    else if (ev.type === "error") throw new Error(ev.message);
    else if (ev.type === "result") report = ev.report;
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) { handle(buf.slice(0, i)); buf = buf.slice(i + 1); }
  }
  handle(buf);
  if (!report) throw new Error("No result received.");
  return report;
}
