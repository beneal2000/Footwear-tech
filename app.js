let DATA = {papers: [], news: [], patents: [], patent_searches: []};
let paperTag = "全部", query = "";
const $ = s => document.querySelector(s);
const esc = s => (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const hit = (...txt) => !query || txt.join(" ").toLowerCase().includes(query);

function render() {
  // News
  const news = DATA.news.filter(n => hit(n.title, n.abstract, n.source));
  $("#newsGrid").innerHTML = news.map(n => `
    <a class="card" href="${esc(n.url)}" target="_blank" rel="noopener">
      <div class="meta"><span>${esc(n.date)}</span><span class="tag">${esc(n.source)}</span></div>
      <h3>${esc(n.title)}</h3><p>${esc(n.abstract)}</p><span class="go">阅读原文 ›</span></a>`).join("");
  $("#newsEmpty").hidden = news.length > 0;

  // Papers
  const tags = ["全部", ...new Set(DATA.papers.map(p => p.tag).filter(Boolean))];
  $("#paperChips").innerHTML = tags.map(t =>
    `<button class="chip ${t === paperTag ? "on" : ""}" data-tag="${esc(t)}">${esc(t)}</button>`).join("");
  document.querySelectorAll(".chip").forEach(c => c.onclick = () => { paperTag = c.dataset.tag; render(); });
  const papers = DATA.papers.filter(p =>
    (paperTag === "全部" || p.tag === paperTag) && hit(p.title, p.abstract, p.venue, (p.authors || []).join(" "), p.doi));
  $("#paperGrid").innerHTML = papers.map(p => `
    <a class="card" href="${esc(p.url)}" target="_blank" rel="noopener">
      <div class="meta"><span>${esc(p.date)}</span><span class="tag">${esc(p.tag || "")}</span><span>${esc(p.source)}</span></div>
      <h3>${esc(p.title)}</h3>
      <p class="authors">${esc((p.authors || []).join(", "))}${p.venue ? " · " + esc(p.venue) : ""}</p>
      ${p.abstract ? `<p>${esc(p.abstract)}</p>` : ""}
      ${p.doi ? `<p>DOI: ${esc(p.doi)}</p>` : ""}
      <span class="go">查看论文 ›</span></a>`).join("");
  $("#paperEmpty").hidden = papers.length > 0;

  // Patents: real records (when OPS/Lens keys configured)
  $("#patentGrid").innerHTML = (DATA.patents || []).filter(p => hit(p.title, p.number, p.brand))
    .map(p => `<a class="card" href="${esc(p.url)}" target="_blank" rel="noopener">
      <div class="meta"><span>${esc(p.date)}</span><span class="tag">${esc(p.source || "")}</span><span>${esc(p.number || "")}</span></div>
      <h3>${esc(p.title)}</h3><p>${esc(p.abstract || "")}</p><span class="go">查看专利原文 ›</span></a>`).join("");

  // Patent search entries per brand
  const searches = DATA.patent_searches.filter(s => hit(s.brand, s.applicant, (s.cpc || []).join(" ")));
  $("#patentSearchGrid").innerHTML = searches.map(s => `
    <div class="card">
      <div class="meta"><span class="tag">${esc(s.brand)}</span><span>${esc(s.applicant)}</span></div>
      <h3>${esc(s.brand)} · 最新公开专利</h3>
      <p>CPC：${esc((s.cpc || []).join(" / "))}<br>${esc(s.note || "")}</p>
      <div class="patent-links">${Object.entries(s.links || {}).map(([k, v]) =>
        `<a href="${esc(v)}" target="_blank" rel="noopener">${esc(k)}</a>`).join("")}</div>
    </div>`).join("");

  $("#statNews").textContent = DATA.news.length;
  $("#statPapers").textContent = DATA.papers.length;
  $("#statPatents").textContent = DATA.patent_searches.length + (DATA.patents || []).length;
}

$("#search").addEventListener("input", e => { query = e.target.value.trim().toLowerCase(); render(); });
$("#footYear").textContent = new Date().getFullYear();

fetch("data/data.json").then(r => r.json()).then(d => {
  DATA = d;
  const t = d.updated_at ? new Date(d.updated_at) : null;
  if (t) {
    $("#updatedAt").textContent = "数据更新至 " + t.toLocaleString("zh-CN", {hour12: false});
    $("#navDate").textContent = t.toLocaleDateString("zh-CN") + " 更新";
  }
  render();
}).catch(() => { $("#updatedAt").textContent = "数据文件尚未生成，请先运行抓取脚本。"; });
