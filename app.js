(() => {
  "use strict";

  const WATCH = [
    {
      id: "CRCL",
      symbol: "CRCL",
      name: "Circle",
      kind: "stock",
      yahoo: "CRCL",
      keywords: ["crcl", "circle", "usdc", "circle internet", "circle ipo"],
    },
    {
      id: "BTC",
      symbol: "BTC",
      name: "Bitcoin",
      kind: "crypto",
      gecko: "bitcoin",
      keywords: ["btc", "bitcoin", "비트코인"],
    },
    {
      id: "ETH",
      symbol: "ETH",
      name: "Ethereum",
      kind: "crypto",
      gecko: "ethereum",
      keywords: ["eth", "ethereum", "이더리움", "ether"],
    },
    {
      id: "LINK",
      symbol: "LINK",
      name: "Chainlink",
      kind: "crypto",
      gecko: "chainlink",
      keywords: ["link", "chainlink", "체인링크", "ccip"],
    },
    {
      id: "SOL",
      symbol: "SOL",
      name: "Solana",
      kind: "crypto",
      gecko: "solana",
      keywords: ["sol", "solana", "솔라나"],
    },
    {
      id: "ONDO",
      symbol: "ONDO",
      name: "Ondo",
      kind: "crypto",
      gecko: "ondo-finance",
      keywords: ["ondo", "ousg", "rwa", "tokenized treasury"],
    },
    {
      id: "TAO",
      symbol: "TAO",
      name: "Bittensor",
      kind: "crypto",
      gecko: "bittensor",
      keywords: ["tao", "bittensor", "subnet", "비트텐서"],
    },
    {
      id: "XRP",
      symbol: "XRP",
      name: "XRP",
      kind: "crypto",
      gecko: "ripple",
      keywords: ["xrp", "ripple", "리플"],
    },
  ];

  const MACRO_TOPICS = [
    { id: "FOMC", label: "FOMC", keywords: ["fomc", "rate decision", "fed decision", "federal open market"] },
    { id: "CPI", label: "CPI/물가", keywords: ["cpi", "inflation", "pce", "물가", "인플레이션"] },
    { id: "Rates", label: "금리", keywords: ["interest rate", "fed funds", "rate cut", "rate hike", "금리"] },
    { id: "Liquidity", label: "유동성", keywords: ["liquidity", "balance sheet", "qt", "qe", "treasury", "dxy"] },
    { id: "Jobs", label: "고용", keywords: ["payroll", "unemployment", "jobs report", "nfp", "고용"] },
  ];

  const FEEDS = [
    { id: "coindesk", name: "CoinDesk", category: "crypto", url: "https://www.coindesk.com/arc/outboundfeeds/rss/" },
    { id: "cointelegraph", name: "CoinTelegraph", category: "crypto", url: "https://cointelegraph.com/rss" },
    { id: "decrypt", name: "Decrypt", category: "crypto", url: "https://decrypt.co/feed" },
    { id: "theblock", name: "The Block", category: "crypto", url: "https://www.theblock.co/rss.xml" },
    { id: "bitcoinmagazine", name: "Bitcoin Magazine", category: "crypto", url: "https://bitcoinmagazine.com/.rss/full/" },
    {
      id: "yahoo-watch",
      name: "Yahoo · CRCL/관련",
      category: "stocks",
      url: "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CRCL,COIN,MSTR,HOOD&region=US&lang=en-US",
    },
    { id: "lynalden", name: "Lyn Alden", category: "guru", url: "https://www.lynalden.com/feed/" },
    { id: "bankless", name: "Bankless", category: "guru", url: "https://www.bankless.com/feed" },
    { id: "vitalik", name: "Vitalik Blog", category: "guru", url: "https://vitalik.eth.limo/feed.xml" },
    { id: "a16z", name: "a16z Crypto", category: "guru", url: "https://a16zcrypto.com/posts/feed/" },
    { id: "fed-all", name: "Fed Press", category: "macro", url: "https://www.federalreserve.gov/feeds/press_all.xml" },
    { id: "fed-monetary", name: "Fed Monetary", category: "macro", url: "https://www.federalreserve.gov/feeds/press_monetary.xml" },
    { id: "fed-speeches", name: "Fed Speeches", category: "macro", url: "https://www.federalreserve.gov/feeds/speeches.xml" },
    { id: "cnbc-finance", name: "CNBC Finance", category: "macro", url: "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664" },
    { id: "bbc-business", name: "BBC Business", category: "macro", url: "https://feeds.bbci.co.uk/news/business/rss.xml" },
    { id: "calculatedrisk", name: "Calculated Risk", category: "macro", url: "https://feeds.feedburner.com/CalculatedRisk" },
  ];

  // 시간대 오프셋 큰 순(동→서): Seoul → London → New York → LA
  const WORLD_CLOCKS = [
    { id: "seoul", label: "SEOUL", tz: "Asia/Seoul" },
    { id: "london", label: "LONDON", tz: "Europe/London" },
    { id: "newyork", label: "NY", tz: "America/New_York" },
    { id: "la", label: "LA", tz: "America/Los_Angeles" },
  ];

  const TOP_N = 5;

  const state = {
    items: [],
    prices: {},
    bithumb: {},
    sourceStatus: {},
    category: "crypto",
    asset: null,
    query: "",
    loading: false,
  };

  const els = {
    feed: document.getElementById("feed"),
    status: document.getElementById("status"),
    count: document.getElementById("feed-count"),
    title: document.getElementById("feed-title"),
    updated: document.getElementById("last-updated"),
    refresh: document.getElementById("btn-refresh"),
    search: document.getElementById("search"),
    sources: document.getElementById("source-list"),
    watchCards: document.getElementById("watch-cards"),
    bithumbCards: document.getElementById("bithumb-cards"),
    assetFilters: document.getElementById("asset-filters"),
    macroChips: document.getElementById("macro-chips"),
    worldClocks: document.getElementById("world-clocks"),
    ledTrack: document.getElementById("led-track"),
    briefingSchedule: document.getElementById("briefing-schedule"),
    historyList: document.getElementById("history-list"),
    historyView: document.getElementById("history-view"),
    btnHistoryLatest: document.getElementById("btn-history-latest"),
    btnHistoryToggle: document.getElementById("btn-history-toggle"),
    summaryModal: document.getElementById("summary-modal"),
    summaryTitle: document.getElementById("summary-title"),
    summaryMeta: document.getElementById("summary-meta"),
    summaryBody: document.getElementById("summary-body"),
    summarySource: document.getElementById("summary-source"),
    summaryClose: document.getElementById("summary-close"),
  };

  function textOf(node, selectors) {
    for (const sel of selectors) {
      const el = node.querySelector(sel);
      if (el?.textContent?.trim()) return el.textContent.trim();
    }
    return "";
  }

  function attrOf(node, selectors, attr) {
    for (const sel of selectors) {
      const el = node.querySelector(sel);
      const v = el?.getAttribute?.(attr);
      if (v) return v.trim();
    }
    return "";
  }

  function stripHtml(html) {
    const d = document.createElement("div");
    d.innerHTML = html || "";
    return (d.textContent || "").replace(/\s+/g, " ").trim();
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function parseRss(xmlText, feed) {
    const doc = new DOMParser().parseFromString(xmlText, "application/xml");
    if (doc.querySelector("parsererror")) throw new Error("XML parse failed");
    const nodes = [...doc.querySelectorAll("item"), ...doc.querySelectorAll("entry")];
    return nodes
      .map((node) => {
        const title = textOf(node, ["title"]);
        const link =
          attrOf(node, ["link[href]"], "href") ||
          textOf(node, ["link", "guid", "id"]);
        const dateRaw = textOf(node, ["pubDate", "published", "updated", "dc\\:date", "date"]);
        const summary = stripHtml(
          textOf(node, ["description", "summary", "content", "content\\:encoded"])
        );
        const ts = dateRaw ? Date.parse(dateRaw) : NaN;
        return enrichItem({
          id: `${feed.id}:${link || title}`,
          title,
          link,
          summary,
          date: Number.isFinite(ts) ? ts : 0,
          source: feed.name,
          category: feed.category,
          feedId: feed.id,
        });
      })
      .filter((x) => x.title && x.link);
  }

  function enrichItem(item) {
    const hay = `${item.title} ${item.summary}`.toLowerCase();
    const assets = WATCH.filter((w) =>
      w.keywords.some((k) => {
        if (k.length <= 3) {
          const re = new RegExp(`(^|[^a-z0-9])${k}([^a-z0-9]|$)`, "i");
          return re.test(hay);
        }
        return hay.includes(k);
      })
    ).map((w) => w.symbol);

    const macros = MACRO_TOPICS.filter((m) =>
      m.keywords.some((k) => hay.includes(k))
    ).map((m) => m.id);

    let score = 0;
    score += assets.length * 10;
    score += macros.length * 4;
    if (item.category === "guru") score += 3;
    if (item.category === "macro") score += 3;
    if (assets.length) score += 6;
    // 최신성 가점 / 오래된 기사 페널티
    if (item.date) {
      const ageH = (Date.now() - item.date) / 3600000;
      if (ageH < 0) score -= 20;
      else if (ageH < 6) score += 18;
      else if (ageH < 24) score += 12;
      else if (ageH < 72) score += 5;
      else if (ageH < 168) score -= 8;
      else score -= 40;
    } else {
      score -= 15;
    }

    return { ...item, assets, macros, score, watchHit: assets.length > 0 };
  }

  function getTzParts(tz) {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
      hourCycle: "h23",
    }).formatToParts(new Date());
    const get = (type) => Number(parts.find((p) => p.type === type)?.value || 0);
    return { hour: get("hour") % 24, minute: get("minute"), second: get("second") };
  }

  function formatClockTime(tz) {
    const { hour, minute, second } = getTzParts(tz);
    return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}`;
  }

  function formatClockDate(tz) {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(new Date());
  }

  function setMatrixClock(cell, tz) {
    const timeEl = cell.querySelector(".clock-digital");
    const dayEl = cell.querySelector(".clock-day");
    if (timeEl) timeEl.textContent = formatClockTime(tz);
    if (dayEl) dayEl.textContent = formatClockDate(tz);
  }

  function renderWorldClocks() {
    if (!els.worldClocks) return;
    els.worldClocks.innerHTML = WORLD_CLOCKS.map(
      (c) => `
      <div class="clock-cell" data-tz="${c.tz}">
        <span class="clock-city">${c.label}</span>
        <div class="matrix-clock" aria-hidden="true">
          <span class="clock-digital">${formatClockTime(c.tz)}</span>
        </div>
        <span class="clock-day">${formatClockDate(c.tz)}</span>
      </div>`
    ).join("");
    tickWorldClocks();
  }

  function tickWorldClocks() {
    if (!els.worldClocks) return;
    els.worldClocks.querySelectorAll(".clock-cell").forEach((cell) => {
      setMatrixClock(cell, cell.dataset.tz);
    });
  }

  async function fetchViaLocal(url) {
    const res = await fetch(`/api/rss?url=${encodeURIComponent(url)}`);
    if (!res.ok) throw new Error(`local ${res.status}`);
    const data = await res.json();
    if (!data?.xml) throw new Error("local empty");
    return data.xml;
  }

  async function fetchViaAllOrigins(url) {
    const res = await fetch(`https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`);
    if (!res.ok) throw new Error(`allorigins ${res.status}`);
    return res.text();
  }

  async function fetchViaRss2Json(url) {
    const res = await fetch(
      `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(url)}`
    );
    if (!res.ok) throw new Error(`rss2json ${res.status}`);
    const data = await res.json();
    if (data.status !== "ok" || !Array.isArray(data.items)) throw new Error("rss2json bad");
    return data.items.map((item) =>
      enrichItem({
        id: `${url}:${item.link || item.guid}`,
        title: item.title,
        link: item.link || item.guid,
        summary: stripHtml(item.description || item.content || ""),
        date: Date.parse(item.pubDate) || 0,
        source: "",
        category: "crypto",
        feedId: "rss2json",
      })
    );
  }

  async function loadFeed(feed) {
    state.sourceStatus[feed.id] = { name: feed.name, state: "load", detail: "…" };
    renderSources();
    try {
      let xml;
      try {
        xml = await fetchViaLocal(feed.url);
      } catch {
        xml = await fetchViaAllOrigins(feed.url);
      }
      const items = parseRss(xml, feed);
      state.sourceStatus[feed.id] = { name: feed.name, state: "ok", detail: `${items.length}` };
      return items;
    } catch (err1) {
      try {
        const items = (await fetchViaRss2Json(feed.url)).map((x) => ({
          ...x,
          source: feed.name,
          category: feed.category,
          feedId: feed.id,
        }));
        state.sourceStatus[feed.id] = { name: feed.name, state: "ok", detail: `${items.length}` };
        return items;
      } catch (err2) {
        state.sourceStatus[feed.id] = { name: feed.name, state: "fail", detail: "실패" };
        console.warn(feed.name, err1, err2);
        return [];
      }
    }
  }

  async function fetchJson(url) {
    try {
      const res = await fetch(`/api/json?url=${encodeURIComponent(url)}`);
      if (res.ok) return res.json();
    } catch {
      /* fall through */
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error(`json ${res.status}`);
    return res.json();
  }

  async function loadPrices() {
    const geckoIds = WATCH.filter((w) => w.gecko).map((w) => w.gecko).join(",");
    try {
      const data = await fetchJson(
        `https://api.coingecko.com/api/v3/simple/price?ids=${geckoIds}&vs_currencies=usd&include_24hr_change=true`
      );
      for (const w of WATCH) {
        if (!w.gecko || !data[w.gecko]) continue;
        state.prices[w.id] = {
          price: data[w.gecko].usd,
          change: data[w.gecko].usd_24h_change,
        };
      }
    } catch (err) {
      console.warn("coingecko", err);
    }

    try {
      const y = await fetchJson(
        "https://query1.finance.yahoo.com/v8/finance/chart/CRCL?interval=1d&range=5d"
      );
      const meta = y?.chart?.result?.[0]?.meta;
      if (meta?.regularMarketPrice != null) {
        const price = meta.regularMarketPrice;
        const prev = meta.chartPreviousClose || meta.previousClose;
        const change = prev ? ((price - prev) / prev) * 100 : null;
        state.prices.CRCL = { price, change };
      }
    } catch (err) {
      console.warn("yahoo CRCL", err);
    }
  }

  async function loadBithumbPrices() {
    try {
      const data = await fetchJson("https://api.bithumb.com/public/ticker/ALL_KRW");
      if (String(data?.status) !== "0000" || !data?.data) throw new Error("bithumb bad");
      const next = {};
      for (const w of WATCH) {
        if (w.kind !== "crypto") continue;
        const row = data.data[w.symbol];
        if (!row || typeof row !== "object") continue;
        const price = Number(row.closing_price);
        const change = Number(row.fluctate_rate_24H);
        if (!Number.isFinite(price)) continue;
        next[w.symbol] = {
          price,
          change: Number.isFinite(change) ? change : null,
        };
      }
      state.bithumb = next;
    } catch (err) {
      console.warn("bithumb", err);
    }
  }

  function formatPrice(n) {
    if (n == null || Number.isNaN(n)) return "—";
    if (n >= 1000) {
      return `$${n.toLocaleString("en-US", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      })}`;
    }
    if (n >= 1) {
      return `$${n.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;
    }
    return `$${n.toLocaleString("en-US", {
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    })}`;
  }

  function formatKrw(n) {
    if (n == null || Number.isNaN(n)) return "—";
    if (n >= 1000) {
      return `₩${Math.round(n).toLocaleString("ko-KR")}`;
    }
    if (n >= 1) {
      return `₩${n.toLocaleString("ko-KR", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      })}`;
    }
    return `₩${n.toLocaleString("ko-KR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    })}`;
  }

  function formatChange(n) {
    if (n == null || Number.isNaN(n)) return { text: "—", cls: "flat" };
    const sign = n > 0 ? "+" : "";
    return {
      text: `${sign}${n.toFixed(2)}%`,
      cls: n > 0.05 ? "up" : n < -0.05 ? "down" : "flat",
    };
  }

  function formatTime(ts) {
    if (!ts) return "시간 미상";
    const diff = Date.now() - ts;
    const m = Math.floor(diff / 60000);
    if (m < 1) return "방금";
    if (m < 60) return `${m}분 전`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}시간 전`;
    const d = Math.floor(h / 24);
    if (d < 7) return `${d}일 전`;
    return new Date(ts).toLocaleString("ko-KR", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function catLabel(cat) {
    return {
      crypto: "Crypto",
      stocks: "Stock",
      macro: "Macro",
      guru: "Guru",
    }[cat] || cat;
  }

  function titleForCategory(cat) {
    return {
      guru: "Guru Main Issues",
      macro: "Macro Main Issues",
      crypto: "Crypto Main Issues",
      stocks: "Stock Main Issues",
    }[cat] || "Main Issues";
  }

  function importanceScore(item) {
    let s = item.score || 0;
    if (item.watchHit) s += 18;
    if (state.asset && item.assets.includes(state.asset)) s += 25;
    if (state.category === "macro" && item.macros.length) s += 8;
    return s;
  }

  function filteredItems() {
    const q = state.query.trim().toLowerCase();
    return state.items
      .filter((item) => {
        if (state.asset && !item.assets.includes(state.asset)) return false;
        if (item.category !== state.category) return false;
        if (!q) return true;
        return `${item.title} ${item.summary} ${item.source} ${item.assets.join(" ")}`
          .toLowerCase()
          .includes(q);
      })
      .sort((a, b) => {
        const sa = importanceScore(a);
        const sb = importanceScore(b);
        if (sb !== sa) return sb - sa;
        return b.date - a.date;
      });
  }

  function setActiveTab(cat) {
    state.category = cat;
    document.querySelectorAll(".cat-tab").forEach((c) => {
      const on = c.dataset.cat === cat;
      c.classList.toggle("active", on);
      c.setAttribute("aria-selected", on ? "true" : "false");
    });
    if (els.macroChips) els.macroChips.hidden = cat !== "macro";
  }

  function renderWatchCards() {
    els.watchCards.innerHTML = WATCH.map((w) => {
      const p = state.prices[w.id];
      const chg = formatChange(p?.change);
      const active = state.asset === w.symbol ? "active" : "";
      return `
        <button class="watch-tile ${active} ${chg.cls}" type="button" data-asset="${w.symbol}" title="${w.name}">
          <span class="watch-sym">${w.symbol}</span>
          <span class="watch-chg ${chg.cls}">${chg.text}</span>
          <span class="watch-price">${formatPrice(p?.price)}</span>
        </button>`;
    }).join("");

    els.watchCards.querySelectorAll(".watch-tile").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sym = btn.dataset.asset;
        const watch = WATCH.find((w) => w.symbol === sym);
        state.asset = state.asset === sym ? null : sym;
        if (state.asset && watch) {
          setActiveTab(watch.kind === "stock" ? "stocks" : "crypto");
        }
        renderWatchCards();
        renderBithumbCards();
        renderFeed();
      });
    });
  }

  function renderBithumbCards() {
    if (!els.bithumbCards) return;
    const coins = WATCH.filter((w) => w.kind === "crypto");
    els.bithumbCards.innerHTML = coins
      .map((w) => {
        const p = state.bithumb[w.symbol];
        const chg = formatChange(p?.change);
        const active = state.asset === w.symbol ? "active" : "";
        return `
        <button class="watch-tile bithumb-tile ${active} ${chg.cls}" type="button" data-asset="${w.symbol}" title="Bithumb ${w.name}">
          <span class="watch-sym">${w.symbol}</span>
          <span class="watch-chg ${chg.cls}">${chg.text}</span>
          <span class="watch-price">${formatKrw(p?.price)}</span>
        </button>`;
      })
      .join("");

    els.bithumbCards.querySelectorAll(".watch-tile").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sym = btn.dataset.asset;
        state.asset = state.asset === sym ? null : sym;
        if (state.asset) setActiveTab("crypto");
        renderWatchCards();
        renderBithumbCards();
        renderFeed();
      });
    });
  }

  function renderAssetFilters() {
    /* 워치 스트립에 ALL/종목 통합 */
  }

  function renderMacroChips() {
    els.macroChips.innerHTML = MACRO_TOPICS.map((m) => {
      const hits = state.items.filter((item) => item.macros.includes(m.id)).length;
      return `
        <button class="macro-chip" type="button" data-macro="${m.id}">
          <b>${m.label}</b>
          <span class="${hits ? "hit" : "none"}">${hits ? `${hits}` : "—"}</span>
        </button>`;
    }).join("");

    els.macroChips.querySelectorAll(".macro-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        setActiveTab("macro");
        state.query = btn.dataset.macro === "Rates" ? "rate" : btn.dataset.macro.toLowerCase();
        if (els.search) els.search.value = state.query;
        renderFeed();
      });
    });
  }

  function renderSources() {
    els.sources.innerHTML = FEEDS.map((f) => {
      const st = state.sourceStatus[f.id] || { state: "load", detail: "대기" };
      return `<li><strong>${f.name}</strong><span class="${st.state}">${st.detail}</span></li>`;
    }).join("");
  }

  function closeSummaryModal() {
    if (!els.summaryModal) return;
    els.summaryModal.hidden = true;
    document.body.classList.remove("modal-open");
  }

  function openSummaryModalShell(item) {
    if (!els.summaryModal) return;
    els.summaryModal.hidden = false;
    document.body.classList.add("modal-open");
    if (els.summaryTitle) els.summaryTitle.textContent = item.title || "요약";
    if (els.summaryMeta) {
      els.summaryMeta.textContent = `${item.source || "출처"} · ${catLabel(item.category)} · Gemini 요약 중…`;
    }
    if (els.summaryBody) els.summaryBody.textContent = "Gemini가 이슈를 한국어로 정리하는 중…";
    if (els.summarySource) {
      if (item.link) {
        els.summarySource.href = item.link;
        els.summarySource.hidden = false;
      } else {
        els.summarySource.hidden = true;
      }
    }
  }

  async function summarizeIssue(item) {
    openSummaryModalShell(item);
    try {
      const res = await fetch("/api/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: item.title,
          summary: item.summary,
          link: item.link,
          source: item.source,
          category: item.category,
          assets: item.assets || [],
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
      if (els.summaryBody) els.summaryBody.textContent = data.markdown || "요약 결과가 없습니다.";
      if (els.summaryMeta) {
        const mode = data.mode === "gemini" ? "Gemini" : "로컬 추출";
        const cache = data.cached ? " · 캐시" : "";
        els.summaryMeta.textContent = `${item.source || "출처"} · ${catLabel(item.category)} · ${mode}${cache}`;
      }
    } catch (err) {
      if (els.summaryBody) {
        els.summaryBody.textContent = `요약 실패: ${err.message || err}`;
      }
      if (els.summaryMeta) {
        els.summaryMeta.textContent = `${item.source || "출처"} · 오류`;
      }
    }
  }

  function renderFeed() {
    const all = filteredItems();
    const items = all.slice(0, TOP_N);
    els.title.textContent = titleForCategory(state.category);
    if (els.count) els.count.textContent = "";
    if (els.macroChips) els.macroChips.hidden = state.category !== "macro";
    if (!items.length) {
      els.feed.innerHTML = `<div class="empty">No top issues in this tab. Try another category.</div>`;
      return;
    }
    els.feed.innerHTML = items
      .map((item, i) => {
        const rank = i + 1;
        const tags = [
          ...item.assets.map((a) => `<span class="tag">${a}</span>`),
          ...item.macros.map((m) => `<span class="tag">${m}</span>`),
        ].join("");
        return `
      <button class="card ranked ${item.watchHit ? "hot" : ""} rank-${rank}" type="button" data-idx="${i}" style="animation-delay:${i * 40}ms">
        <div class="rank-mark" aria-label="rank ${rank}">${rank}</div>
        <div class="card-body">
          <div class="card-top">
            <span class="badge ${item.category}">${catLabel(item.category)}</span>
            <span class="card-source">${escapeHtml(item.source)}</span>
            <span class="card-time">${formatTime(item.date)}</span>
            <span class="card-hint">Gemini 요약</span>
          </div>
          <h4>${escapeHtml(item.title)}</h4>
          ${item.summary ? `<p>${escapeHtml(item.summary)}</p>` : ""}
          ${tags ? `<div class="card-tags">${tags}</div>` : ""}
        </div>
      </button>`;
      })
      .join("");

    els.feed.querySelectorAll(".card").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = Number(btn.dataset.idx);
        const item = items[idx];
        if (item) summarizeIssue(item);
      });
    });
  }

  function setStatus(msg, isError = false) {
    if (!els.status) return;
    if (!msg) {
      els.status.hidden = true;
      els.status.classList.add("hidden");
      return;
    }
    // Keep mobile clean: only surface errors in status.
    if (!isError && window.matchMedia("(max-width: 860px)").matches) {
      els.status.hidden = true;
      return;
    }
    els.status.hidden = false;
    els.status.classList.remove("hidden");
    els.status.classList.toggle("error", isError);
    els.status.textContent = msg;
  }

  function setHistoryExpanded(open) {
    if (!els.historyList || !els.btnHistoryToggle) return;
    els.historyList.hidden = !open;
    els.btnHistoryToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  async function refresh() {
    if (state.loading) return;
    state.loading = true;
    els.refresh.disabled = true;
    setStatus("워치리스트 · Guru · 연준 피드를 수집 중…");
    renderSources();
    renderWatchCards();

    const [batches] = await Promise.all([
      Promise.all(FEEDS.map((f) => loadFeed(f))),
      loadPrices().then(() => renderWatchCards()),
      loadBithumbPrices().then(() => renderBithumbCards()),
    ]);

    const seen = new Set();
    state.items = batches
      .flat()
      .filter((item) => {
        if (seen.has(item.link)) return false;
        seen.add(item.link);
        return true;
      })
      .sort((a, b) => b.date - a.date);

    const ok = Object.values(state.sourceStatus).filter((s) => s.state === "ok").length;
    const fail = FEEDS.length - ok;
    const watchHits = state.items.filter((x) => x.watchHit).length;
    els.updated.textContent = `Updated ${new Date().toLocaleTimeString("en-US")}`;
    setStatus(
      `${ok}/${FEEDS.length} 소스 · 주시 매칭 ${watchHits}건 · 전체 ${state.items.length}건${fail ? ` · 실패 ${fail}` : ""}`
    );
    renderSources();
    renderMacroChips();
    renderFeed();
    state.loading = false;
    els.refresh.disabled = false;
  }

  document.querySelectorAll(".cat-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.query = "";
      if (els.search) els.search.value = "";
      setActiveTab(btn.dataset.cat);
      renderFeed();
    });
  });

  els.search?.addEventListener("input", () => {
    state.query = els.search.value;
    renderFeed();
  });

  function markdownToTicker(md) {
    if (!md) return "No briefing yet · auto every 8 hours";
    const strategy = (md.match(/🎯[^\n]+/) || [""])[0].trim();
    const plain = md
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/^#{1,6}\s*/gm, "")
      .replace(/[*_`>#]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    const core = strategy || plain.slice(0, 420);
    return `${core}   ···   ${plain.slice(0, 900)}`;
  }

  function setLedText(text) {
    if (!els.ledTrack) return;
    const line = text || "Waiting for briefing…";
    els.ledTrack.textContent = `${line}     ///     ${line}     ///     `;
  }

  function formatHistoryLabel(item) {
    const d = new Date((item.mtime || 0) * 1000);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  async function loadBriefingStatus() {
    try {
      const res = await fetch("/api/briefing/status");
      const data = await res.json();
      const next = data.next_run_at
        ? new Date(data.next_run_at * 1000).toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
          })
        : "--:--";
      const state = data.running ? "RUNNING" : "AUTO 8h";
      if (els.briefingSchedule) {
        els.briefingSchedule.textContent = `${state} · next ${next}`;
      }
    } catch {
      if (els.briefingSchedule) els.briefingSchedule.textContent = "AUTO · every 8h";
    }
  }

  function openHistoryPanel(markdown, { keepLed = true } = {}) {
    if (!els.historyView) return;
    setHistoryExpanded(true);
    els.historyView.hidden = false;
    els.historyView.textContent = markdown || "";
    document.getElementById("briefing-history")?.classList.add("is-open");
    if (keepLed) setLedText(markdownToTicker(markdown || ""));
  }

  async function loadLatestBriefing() {
    try {
      const res = await fetch("/api/briefing/latest");
      const data = await res.json();
      if (!data.exists) {
        setLedText(data.hint || "Waiting for auto briefing…");
        return;
      }
      setLedText(markdownToTicker(data.markdown || ""));
    } catch (err) {
      setLedText(
        "Gemini briefing needs local server · Mac에서 server.py 실행 + .env에 GEMINI_API_KEY 설정"
      );
    }
  }

  async function loadBriefingHistory() {
    if (!els.historyList) return;
    try {
      const res = await fetch("/api/briefing/history?limit=40");
      const data = await res.json();
      const items = data.items || [];
      if (!items.length) {
        els.historyList.innerHTML = "<li class='meta' style='color:#8fbf9a'>No history yet</li>";
        return;
      }
      els.historyList.innerHTML = items
        .map(
          (it) =>
            `<li><button type="button" data-id="${escapeHtml(it.id)}">${formatHistoryLabel(it)}</button></li>`
        )
        .join("");
      els.historyList.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", async () => {
          els.historyList.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          await openHistoryItem(btn.dataset.id);
        });
      });
    } catch {
      els.historyList.innerHTML = "";
    }
  }

  async function openHistoryItem(id) {
    if (!id || !els.historyView) return;
    try {
      const res = await fetch(`/api/briefing/item?id=${encodeURIComponent(id)}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      openHistoryPanel(data.markdown || "");
    } catch (err) {
      openHistoryPanel(`Failed: ${err.message || err}`, { keepLed: false });
    }
  }

  els.btnHistoryToggle?.addEventListener("click", () => {
    const open = els.btnHistoryToggle.getAttribute("aria-expanded") !== "true";
    setHistoryExpanded(open);
    if (!open) {
      if (els.historyView) els.historyView.hidden = true;
      document.getElementById("briefing-history")?.classList.remove("is-open");
    }
  });

  els.btnHistoryLatest?.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/briefing/latest");
      const data = await res.json();
      if (!data.exists) {
        openHistoryPanel(data.hint || "No briefing yet.", { keepLed: false });
        return;
      }
      openHistoryPanel(data.markdown || "");
      loadBriefingHistory();
    } catch (err) {
      openHistoryPanel(`Failed: ${err.message || err}`, { keepLed: false });
    }
  });


  function startMatrixRain() {
    const canvas = document.getElementById("matrix-bg");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const glyphs = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>*+#@$%&=/";

    function paintStatic() {
      const width = (canvas.width = window.innerWidth);
      const height = (canvas.height = window.innerHeight);
      const fontSize = Math.max(13, Math.floor(width / 95));
      const cols = Math.ceil(width / fontSize);
      const rows = Math.ceil(height / fontSize) + 2;

      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, width, height);
      ctx.font = `${fontSize}px "SF Mono", ui-monospace, Menlo, Consolas, monospace`;
      ctx.textBaseline = "top";

      for (let i = 0; i < cols; i += 1) {
        for (let j = 0; j < rows; j += 1) {
          const ch = glyphs[Math.floor(Math.random() * glyphs.length)];
          const bright = Math.random();
          if (bright > 0.82) ctx.fillStyle = "rgba(210, 255, 220, 0.72)";
          else if (bright > 0.45) ctx.fillStyle = "rgba(57, 255, 20, 0.42)";
          else ctx.fillStyle = "rgba(0, 160, 70, 0.22)";
          ctx.fillText(ch, i * fontSize, j * fontSize);
        }
      }
    }

    paintStatic();
    let resizeTimer = 0;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(paintStatic, 120);
    });
  }

  els.refresh.addEventListener("click", refresh);
  els.summaryClose?.addEventListener("click", closeSummaryModal);
  els.summaryModal?.addEventListener("click", (e) => {
    if (e.target === els.summaryModal) closeSummaryModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSummaryModal();
  });

  startMatrixRain();
  renderWorldClocks();
  setInterval(tickWorldClocks, 1000);
  setActiveTab(state.category);
  renderWatchCards();
  renderBithumbCards();
  renderMacroChips();
  renderSources();
  loadLatestBriefing();
  loadBriefingHistory();
  loadBriefingStatus();
  refresh();
  setInterval(refresh, 5 * 60 * 1000);
  setInterval(() => {
    loadLatestBriefing();
    loadBriefingHistory();
    loadBriefingStatus();
  }, 60 * 1000);
})();
