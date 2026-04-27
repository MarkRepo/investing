(function () {
  "use strict";

  const dataEl = document.getElementById("quotes-data");
  if (!dataEl) return;
  const data = JSON.parse(dataEl.textContent);

  const klineDom = document.getElementById("kline-chart");
  const intradayDom = document.getElementById("intraday-chart");
  const klineChart = klineDom && window.echarts ? echarts.init(klineDom) : null;
  const intradayChart =
    intradayDom && window.echarts ? echarts.init(intradayDom) : null;

  const MA_WINDOWS = [5, 10, 20, 30, 60];
  const MA_COLORS = {
    5: "#f39c12", 10: "#2980b9", 20: "#9b59b6",
    30: "#16a085", 60: "#c0392b",
  };

  function formatVolume(v) {
    if (v == null || isNaN(v)) return "";
    const a = Math.abs(v);
    // A-share volumes are shares; US too. Use CN-ish formatting for both
    // since the tooltip just needs to be glanceable, not precisely localized.
    if (a >= 1e8) return (v / 1e8).toFixed(2) + "亿";
    if (a >= 1e4) return (v / 1e4).toFixed(1) + "万";
    return Math.round(v).toLocaleString();
  }

  function movingAverage(closes, window) {
    const out = new Array(closes.length).fill(null);
    let sum = 0;
    for (let i = 0; i < closes.length; i++) {
      sum += closes[i];
      if (i >= window) sum -= closes[i - window];
      if (i >= window - 1) out[i] = +(sum / window).toFixed(3);
    }
    return out;
  }

  function klineOption(ohlcv) {
    const dates = ohlcv.map((r) => r.date);
    const candles = ohlcv.map((r) => [r.open, r.close, r.low, r.high]);
    const closes = ohlcv.map((r) => r.close);
    const volumes = ohlcv.map((r) => r.volume || 0);

    // Default view window: last ~120 bars or all if fewer.
    const total = dates.length;
    const startPct = total > 120 ? Math.max(0, 100 - (120 / total) * 100) : 0;

    const maSeries = MA_WINDOWS.map((w) => ({
      name: "MA" + w,
      type: "line",
      data: movingAverage(closes, w),
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 1, color: MA_COLORS[w] },
      itemStyle: { color: MA_COLORS[w] },
      z: 2,
    }));

    return {
      legend: {
        data: ["K", ...MA_WINDOWS.map((w) => "MA" + w)],
        top: 4, left: "center", itemGap: 14, textStyle: { fontSize: 12 },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        formatter: (params) => {
          if (!Array.isArray(params) || !params.length) return "";
          const idx = params[0].dataIndex;
          const date = params[0].axisValue;
          const lines = [`<div style="font-weight:600;margin-bottom:2px">${date}</div>`];
          // Candlestick first
          const kp = params.find((p) => p.seriesName === "K");
          if (kp && Array.isArray(kp.data)) {
            // Candlestick data is [index, open, close, low, high] when passed
            // via axis; for our user-provided arrays it's [open, close, low, high].
            const d = kp.data;
            const [open, close, low, high] = d.length === 5 ? d.slice(1) : d;
            const prev = idx > 0 ? closes[idx - 1] : null;
            const pct = prev ? ((close - prev) / prev) * 100 : null;
            const pctHtml = pct === null
              ? ""
              : ` <span style="color:${pct >= 0 ? "#d62728" : "#2ca02c"}">${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%</span>`;
            lines.push(
              `开 ${open.toFixed(2)}　收 <strong>${close.toFixed(2)}</strong>${pctHtml}`,
              `高 ${high.toFixed(2)}　低 ${low.toFixed(2)}`,
            );
          }
          // MA lines
          const maLines = [];
          for (const p of params) {
            if (!p.seriesName || !p.seriesName.startsWith("MA")) continue;
            const v = p.data;
            if (v === null || v === undefined || isNaN(v)) continue;
            maLines.push(
              `<span style="color:${p.color}">●</span> ${p.seriesName} ${Number(v).toFixed(2)}`,
            );
          }
          if (maLines.length) lines.push(maLines.join("　"));
          // Volume
          const vp = params.find((p) => p.seriesName === "Vol");
          if (vp && vp.data != null) {
            lines.push(`量 ${formatVolume(vp.data)}`);
          }
          return lines.join("<br/>");
        },
      },
      grid: [
        { left: 60, right: 20, top: 36, height: "55%" },
        { left: 60, right: 20, top: "74%", height: "18%" },
      ],
      xAxis: [
        { type: "category", data: dates, gridIndex: 0, axisLabel: { show: false }, boundaryGap: false, axisPointer: { z: 10 } },
        { type: "category", data: dates, gridIndex: 1, boundaryGap: false },
      ],
      yAxis: [
        {
          scale: true, gridIndex: 0, splitLine: { show: true },
          axisPointer: { label: { formatter: (p) => Number(p.value).toFixed(2) } },
        },
        {
          gridIndex: 1, axisLabel: { show: false },
          splitNumber: 2, splitLine: { show: false },
          axisPointer: { label: { formatter: (p) => formatVolume(p.value) } },
        },
      ],
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: [0, 1],
          start: startPct,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          preventDefaultMouseMove: false,
          throttle: 50,
        },
        {
          type: "slider",
          xAxisIndex: [0, 1],
          bottom: 8,
          height: 18,
          start: startPct,
          end: 100,
        },
      ],
      series: [
        {
          name: "K",
          type: "candlestick",
          data: candles,
          itemStyle: {
            color: "#d62728", color0: "#2ca02c",
            borderColor: "#d62728", borderColor0: "#2ca02c",
          },
          z: 3,
        },
        ...maSeries,
        {
          name: "Vol", type: "bar", data: volumes,
          xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: "#8ab0d6" },
        },
      ],
    };
  }

  function intradayOption(rows) {
    // Build full A-share trading session axis: 09:30–11:30 + 13:00–15:00.
    const fullAxis = [];
    const addRange = (h0, m0, h1, m1) => {
      let h = h0, m = m0;
      while (h < h1 || (h === h1 && m <= m1)) {
        fullAxis.push(`${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`);
        m++; if (m === 60) { m = 0; h++; }
      }
    };
    addRange(9, 30, 11, 30);
    addRange(13, 0, 15, 0);

    const priceMap = new Map(rows.map((r) => [r[0], r[1]]));
    const prices = fullAxis.map((t) => priceMap.has(t) ? priceMap.get(t) : null);
    return {
      tooltip: { trigger: "axis" },
      grid: { left: 55, right: 20, top: 20, bottom: 30 },
      xAxis: { type: "category", data: fullAxis, boundaryGap: false,
        min: 0, max: fullAxis.length - 1,
        axisLabel: { interval: (_, v) => ["09:30","10:30","11:30","13:00","14:00","15:00"].includes(v) } },
      yAxis: { scale: true },
      series: [{ type: "line", data: prices, smooth: false, showSymbol: false, connectNulls: false }],
    };
  }

  if (klineChart && data.kline && data.kline.length) {
    klineChart.setOption(klineOption(data.kline));
  }

  // intraday is async — page GET doesn't wait on the adapter network call
  const intradayStatus = document.getElementById("intraday-status");
  async function loadIntraday() {
    if (!intradayChart) return;
    if (!data.has_data) {
      if (intradayStatus) intradayStatus.textContent = "（新票未回补）";
      return;
    }
    try {
      const res = await fetch(`/prices/${data.key}/intraday`);
      const json = await res.json();
      if (json.error) {
        if (intradayStatus) {
          intradayStatus.textContent = "暂不可用: " + json.error.slice(0, 120);
          intradayStatus.classList.add("error");
        }
        return;
      }
      if (!json.bars || !json.bars.length) {
        if (intradayStatus) intradayStatus.textContent = "（非交易时段 / 今日无数据）";
        return;
      }
      intradayChart.setOption(intradayOption(json.bars));
      if (intradayStatus) intradayStatus.textContent = "";
    } catch (e) {
      if (intradayStatus) {
        intradayStatus.textContent = "加载失败: " + e.message;
        intradayStatus.classList.add("error");
      }
    }
  }
  loadIntraday();

  window.addEventListener("resize", () => {
    if (klineChart) klineChart.resize();
    if (intradayChart) intradayChart.resize();
  });

  // period switch (日/周/月 K)
  document.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".period-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const period = btn.dataset.period;
      try {
        const res = await fetch(`/prices/${data.key}/chart?period=${period}`);
        const json = await res.json();
        if (klineChart) klineChart.setOption(klineOption(json.ohlcv), true);
      } catch (e) {
        console.error("chart fetch failed", e);
      }
    });
  });

  // company switcher — give immediate feedback on slow navigations
  const switcher = document.getElementById("company-switch");
  if (switcher) {
    switcher.addEventListener("change", () => {
      const v = switcher.value;
      if (!v || v === data.key) return;
      if (klineChart) klineChart.showLoading();
      if (intradayChart) intradayChart.showLoading();
      location.href = "/prices/" + v;
    });
  }

  // kline maximize — toggles a CSS class that fixed-positions the wrap to viewport
  const fullBtn = document.getElementById("kline-fullscreen");
  const klineWrap = document.getElementById("kline-wrap");
  function setFull(on) {
    if (!klineWrap) return;
    klineWrap.classList.toggle("chart-full", on);
    if (fullBtn) fullBtn.textContent = on ? "⤢ 退出" : "⛶ 最大化";
    if (klineChart) setTimeout(() => klineChart.resize(), 0);
  }
  if (fullBtn) {
    fullBtn.addEventListener("click", () => {
      setFull(!klineWrap.classList.contains("chart-full"));
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && klineWrap && klineWrap.classList.contains("chart-full")) {
      setFull(false);
    }
  });

  // manual refresh (throttled 10s to avoid adapter hammering)
  const refreshBtn = document.getElementById("refresh-btn");
  let throttleUntil = 0;
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      if (Date.now() < throttleUntil) return;
      throttleUntil = Date.now() + 10000;
      const orig = refreshBtn.textContent;
      refreshBtn.disabled = true;
      refreshBtn.textContent = "正在刷新…";
      try {
        const res = await fetch(`/prices/${data.key}/refresh`, { method: "POST" });
        const r = await res.json();
        if (r.ok) {
          location.reload();
        } else {
          alert(
            "刷新失败:\n" +
              (r.daily_error || "") +
              (r.snapshot_error ? "\n快照: " + r.snapshot_error : "")
          );
        }
      } catch (e) {
        alert("刷新请求失败: " + e.message);
      } finally {
        setTimeout(() => {
          refreshBtn.disabled = false;
          refreshBtn.textContent = orig;
        }, 10000);
      }
    });
  }
})();
