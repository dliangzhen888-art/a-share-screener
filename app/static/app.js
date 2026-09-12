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
