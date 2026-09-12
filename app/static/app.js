const form = document.querySelector("#quote-form");
const message = document.querySelector("#quote-message");
const result = document.querySelector("#quote-result");
const nameElement = document.querySelector("#quote-name");
const fieldsElement = document.querySelector("#quote-fields");

const number = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 });
const money = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  maximumFractionDigits: 0,
});

function row(label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value;
  wrapper.append(term, detail);
  return wrapper;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = new FormData(form).get("code").trim();
  message.textContent = "正在查询…";
  result.hidden = true;

  try {
    const response = await fetch(`/api/quote/${encodeURIComponent(code)}`);
    const quote = await response.json();
    if (!response.ok || quote.status !== "ok") throw new Error("行情暂不可用");

    nameElement.textContent = quote.name;
    fieldsElement.replaceChildren(
      row("代码", quote.code),
      row("最新价", number.format(quote.last_price)),
      row("涨跌幅", `${number.format(quote.pct_change)}%`),
      row("成交额", money.format(quote.turnover_amount)),
      row("换手率", `${number.format(quote.turnover_rate)}%`),
      row("量比", number.format(quote.volume_ratio)),
      row("流通市值", money.format(quote.float_market_cap)),
      row("总市值", money.format(quote.total_market_cap)),
      row("数据时间", quote.quote_time),
      row("数据来源", quote.source),
    );
    message.textContent = "";
    result.hidden = false;
  } catch (error) {
    message.textContent = "行情暂不可用，请检查股票代码或稍后重试。";
  }
});

const scanButton = document.querySelector("#scan-button");
const scanMessage = document.querySelector("#scan-message");
const scanStats = document.querySelector("#scan-stats");
const screenResults = document.querySelector("#screen-results");

function candidateCard(candidate) {
  const card = document.createElement("article");
  card.className = "candidate";
  const title = document.createElement("h3");
  title.textContent = `${candidate.name} · ${candidate.code}`;
  const details = document.createElement("dl");
  details.append(
    row("最新价", number.format(candidate.last_price)), row("今日涨幅", `${number.format(candidate.pct_change)}%`),
    row("5日涨幅", `${number.format(candidate.return_5d)}%`), row("量比", number.format(candidate.volume_ratio)),
    row("换手率", `${number.format(candidate.turnover_rate)}%`), row("今日成交额", money.format(candidate.turnover_amount)),
    row("20日平均成交额", money.format(candidate.avg_amount_20d)), row("总市值", money.format(candidate.total_market_cap)),
    row("MA5 / MA10 / MA20", `${number.format(candidate.ma5)} / ${number.format(candidate.ma10)} / ${number.format(candidate.ma20)}`),
    row("RSI14", number.format(candidate.rsi14)), row("MA多头", candidate.ma_bullish ? "是" : "否"),
    row("MA20上移", candidate.ma20_rising ? "是" : "否"),
  );
  card.append(title, details);
  return card;
}

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  scanMessage.textContent = "正在低并发扫描，请耐心等待…";
  scanStats.hidden = true;
  screenResults.replaceChildren();
  try {
    const response = await fetch("/api/screen");
    const payload = await response.json();
    if (!response.ok || payload.status !== "ok") throw new Error("扫描不可用");
    const stats = payload.stats;
    scanStats.replaceChildren(
      row("股票池总数", number.format(stats.universe_total)), row("Stage 1 通过", number.format(stats.stage1_passed)),
      row("Stage 2 通过", number.format(stats.stage2_passed)), row("扫描总耗时", `${number.format(stats.elapsed_seconds)} 秒`),
      row("失败批次数", number.format(stats.failed_batches)), row("历史K请求数量", number.format(stats.history_requests)),
    );
    scanStats.hidden = false;
    screenResults.replaceChildren(...payload.results.map(candidateCard));
    scanMessage.textContent = payload.results.length ? `筛选完成，共 ${payload.results.length} 只。` : "筛选完成，当前无符合条件股票。";
  } catch (error) {
    scanMessage.textContent = "扫描失败，请稍后重试并检查上游接口。";
  } finally {
    scanButton.disabled = false;
  }
});
