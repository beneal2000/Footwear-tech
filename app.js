let DATA = {papers: [], news: [], patents: [], patent_searches: []};
let paperTag = "全部", query = "";
let newsBrand = "全部", paperBrand = "全部", patentBrand = "全部";
const $ = s => document.querySelector(s);
const esc = s => (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const hit = (...txt) => !query || txt.join(" ").toLowerCase().includes(query);
const brandOf = x => x.brands && x.brands.length ? x.brands : (x.brand ? [x.brand] : ["综合/其他"]);
const brandMatch = (x, sel) => sel === "全部" || brandOf(x).includes(sel);
function renderBrandChips(el, items, current, set) {
  const counts = {};
  items.forEach(x => brandOf(x).forEach(b => counts[b] = (counts[b] || 0) + 1));
  const brands = ["全部", ...Object.entries(counts).sort((a, b) => b[1] - a[1]).map(e => e[0])];
  el.innerHTML = brands.map(b =>
    `<button class="chip ${b === current ? "on" : ""}" data-brand="${esc(b)}">${esc(b)}${b === "全部" ? "" : " · " + counts[b]}</button>`).join("");
  el.querySelectorAll(".chip").forEach(c => c.onclick = () => { set(c.dataset.brand); render(); });
}

function render() {
  // News
  renderBrandChips($("#newsBrandChips"), DATA.news, newsBrand, v => newsBrand = v);
  const news = DATA.news.filter(n => brandMatch(n, newsBrand) && hit(n.title, n.title_zh, n.abstract, n.abstract_zh, n.source, brandOf(n).join(" ")));
  $("#newsGrid").innerHTML = news.map(n => `
    <a class="card" href="${esc(n.url)}" target="_blank" rel="noopener">
      <div class="meta"><span>${esc(n.date)}</span><span class="tag">${esc(n.source)}</span><span class="brand">${esc(brandOf(n).join(" / "))}</span></div>
      <h3>${esc(n.title_zh || n.title)}</h3>
      ${n.title_zh && n.title_zh !== n.title ? `<p class="orig">${esc(n.title)}</p>` : ""}
      <p>${esc(n.abstract_zh || n.abstract)}</p><span class="go">阅读原文 ›</span></a>`).join("");
  $("#newsEmpty").hidden = news.length > 0;

  // Papers
  const tags = ["全部", ...new Set(DATA.papers.map(p => p.tag).filter(Boolean))];
  $("#paperChips").innerHTML = tags.map(t =>
    `<button class="chip ${t === paperTag ? "on" : ""}" data-tag="${esc(t)}">${esc(t)}</button>`).join("");
  document.querySelectorAll("#paperChips .chip").forEach(c => c.onclick = () => { paperTag = c.dataset.tag; render(); });
  renderBrandChips($("#paperBrandChips"), DATA.papers, paperBrand, v => paperBrand = v);
  const papers = DATA.papers.filter(p =>
    (paperTag === "全部" || p.tag === paperTag) && brandMatch(p, paperBrand) && hit(p.title, p.title_zh, p.abstract, p.abstract_zh, p.venue, (p.authors || []).join(" "), p.doi, brandOf(p).join(" ")));
  $("#paperGrid").innerHTML = papers.map(p => `
    <a class="card" href="${esc(p.url)}" target="_blank" rel="noopener">
      <div class="meta"><span>${esc(p.date)}</span><span class="tag">${esc(p.tag || "")}</span><span>${esc(p.source)}</span><span class="brand">${esc(brandOf(p).join(" / "))}</span></div>
      <h3>${esc(p.title_zh || p.title)}</h3>
      ${p.title_zh && p.title_zh !== p.title ? `<p class="orig">${esc(p.title)}</p>` : ""}
      <p class="authors">${esc((p.authors || []).join(", "))}${p.venue ? " · " + esc(p.venue) : ""}</p>
      ${p.abstract || p.abstract_zh ? `<p>${esc(p.abstract_zh || p.abstract)}</p>` : ""}
      ${p.doi ? `<p>DOI: ${esc(p.doi)}</p>` : ""}
      <span class="go">查看论文 ›</span></a>`).join("");
  $("#paperEmpty").hidden = papers.length > 0;

  // Patents: brand filter over both real records and search entries
  renderBrandChips($("#patentBrandChips"), [...(DATA.patents || []), ...DATA.patent_searches], patentBrand, v => patentBrand = v);
  $("#patentGrid").innerHTML = (DATA.patents || []).filter(p => brandMatch(p, patentBrand) && hit(p.title, p.number, p.brand, brandOf(p).join(" ")))
    .map(p => `<a class="card" href="${esc(p.url)}" target="_blank" rel="noopener">
      <div class="meta"><span>${esc(p.date)}</span><span class="tag">${esc(p.source || "")}</span><span>${esc(p.number || "")}</span></div>
      <h3>${esc(p.title)}</h3><p>${esc(p.abstract || "")}</p><span class="go">查看专利原文 ›</span></a>`).join("");

  // Patent search entries per brand
  const searches = DATA.patent_searches.filter(s => brandMatch(s, patentBrand) && hit(s.brand, s.applicant, (s.cpc || []).join(" ")));
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
