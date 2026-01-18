// frontend/market.js
(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const elStatus = $("#status");
  const elQuotes = $("#quotes");
  const elNews = $("#news");
  const elAsof = $("#asof");
  const btnRefresh = $("#btnRefresh");

  const LABELS = {
    IVV: "S&P 500",
    SPY: "S&P 500",
    VOO: "S&P 500",
    QQQ: "NASDAQ 100",
    DIA: "Dow Jones",
    IWM: "Russell 2000",
    TLT: "US 20Y Treasury",
    GLD: "Gold",
    USO: "WTI Oil",
    };

  let currentCategory = "general";
  let loading = false;

  const fmt = (n) => {
    if (n === null || n === undefined || n === "") return "-";
    const x = Number(n);
    if (!Number.isFinite(x)) return String(n);
    return x.toLocaleString();
  };

  const pct = (c, pc) => {
    const C = Number(c), PC = Number(pc);
    if (!Number.isFinite(C) || !Number.isFinite(PC) || PC === 0) return "-";
    const v = ((C - PC) / PC) * 100;
    const sign = v >= 0 ? "+" : "";
    return sign + v.toFixed(2) + "%";
  };

  const setLoading = (v) => {
    loading = v;
    btnRefresh.disabled = v;
    elStatus.textContent = v ? "불러오는 중…" : "";
    elStatus.style.display = v ? "block" : "none";
  };

  const quoteCard = (item) => {
    const wrap = document.createElement("div");
    wrap.className = "card2";

    const head = document.createElement("div");
    head.className = "card2-head";

    const sym = document.createElement("div");
    sym.className = "sym";
    // sym.textContent = item.symbol;
    const label = LABELS[item.symbol] ? LABELS[item.symbol] : "";
    sym.innerHTML = label
        ? `${item.symbol}<br><span class="symtag">${label}</span>`
        : `${item.symbol}`;

    const change = document.createElement("div");
    change.className = "chg";

    head.appendChild(sym);
    head.appendChild(change);

    const body = document.createElement("div");
    body.className = "card2-body";

    if (item.error) {
      change.classList.add("muted");
      change.textContent = "N/A";
      const err = document.createElement("div");
      err.className = "muted";
      err.textContent = "데이터 오류: " + item.error;
      body.appendChild(err);
    } else {
      const q = item.quote || {};
      const c = q.c;
      const pc = q.pc;

      const v = document.createElement("div");
      v.className = "price";
      v.textContent = fmt(c);

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = "전일종가 " + fmt(pc);

      const p = pct(c, pc);
      change.textContent = p;

      // 상승/하락 색 느낌만 (과하지 않게)
      if (p !== "-" && p.startsWith("+")) change.classList.add("up");
      else if (p !== "-" && p.startsWith("-")) change.classList.add("down");
      else change.classList.add("muted");

      body.appendChild(v);
      body.appendChild(meta);
    }

    wrap.appendChild(head);
    wrap.appendChild(body);
    return wrap;
  };

  const newsItem = (n) => {
    const row = document.createElement("div");
    row.className = "news-item";

    const h = document.createElement("div");
    h.className = "news-headline";
    h.textContent = n.headline || "(headline 없음)";

    const s = document.createElement("div");
    s.className = "news-summary";
    s.textContent = n.summary || "";

    const f = document.createElement("div");
    f.className = "news-foot";
    const ts = n.datetime ? new Date(n.datetime * 1000).toLocaleString() : "";
    f.textContent = [n.source, ts].filter(Boolean).join(" · ");

    row.appendChild(h);
    row.appendChild(s);
    row.appendChild(f);

    // 링크가 있으면 클릭 가능하게
    if (n.url) {
      row.classList.add("clickable");
      row.addEventListener("click", () => window.open(n.url, "_blank", "noopener,noreferrer"));
    }
    return row;
  };

  async function fetchOverview() {
    setLoading(true);
    try {
      const url = `/api/market/overview?category=${encodeURIComponent(currentCategory)}&news_limit=12`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      // asof (클라 시간)
      elAsof.textContent = new Date().toLocaleString();

      // quotes
      elQuotes.innerHTML = "";
      (data.quotes || []).forEach((q) => elQuotes.appendChild(quoteCard(q)));

      // news
      elNews.innerHTML = "";
      const news = data.news;
      if (Array.isArray(news)) {
        news.forEach((n) => elNews.appendChild(newsItem(n)));
      } else {
        const pre = document.createElement("pre");
        pre.className = "muted";
        pre.textContent = JSON.stringify(news, null, 2);
        elNews.appendChild(pre);
      }
    } catch (e) {
      elQuotes.innerHTML = "";
      elNews.innerHTML = "";
      const err = document.createElement("div");
      err.className = "status error";
      err.textContent = "불러오기 실패: " + (e?.message || String(e));
      elNews.appendChild(err);
    } finally {
      setLoading(false);
    }
  }

  function setCategory(cat) {
    currentCategory = cat;
    $$(".chip").forEach((b) => {
      b.classList.toggle("chip-active", b.dataset.cat === cat);
    });
    fetchOverview();
  }

  // events
  btnRefresh.addEventListener("click", fetchOverview);
  $$(".chip").forEach((b) => b.addEventListener("click", () => setCategory(b.dataset.cat)));

  // init
  fetchOverview();

  async function logout() {
  try {
    await fetch("/api/logout", { method: "POST" });
  } catch (e) {
    // 실패해도 로컬에선 그냥 보내버리자
  } finally {
    location.href = "/login";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btnLogout");
  if (btn) btn.addEventListener("click", logout);
});
})();