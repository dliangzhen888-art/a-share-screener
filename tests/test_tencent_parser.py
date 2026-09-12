from app.market.tencent import normalize_code, parse_tencent_quote


def response(**overrides: str) -> bytes:
    fields = [""] * 50
    values = {
        "1": "贵州茅台",
        "2": "600519",
        "3": "1500.50",
        "4": "1490.00",
        "5": "1495.00",
        "6": "1234",
        "30": "20260912150000",
        "32": "0.70",
        "33": "1510.00",
        "34": "1480.00",
        "37": "250000.50",
        "38": "1.25",
        "44": "10000.00",
        "45": "18000.00",
        "47": "1639.00",
        "48": "1341.00",
        "49": "1.10",
    }
    values.update(overrides)
    for index, value in values.items():
        fields[int(index)] = value
    return f'v_sh600519="{"~".join(fields)}";'.encode("gb18030")


def test_normal_response_and_unit_conversions() -> None:
    quote = parse_tencent_quote(response(), expected_code="600519")
    assert quote is not None
    assert quote.name == "贵州茅台"
    assert quote.volume == 123_400
    assert quote.turnover_amount == 2_500_005_000
    assert quote.float_market_cap == 1_000_000_000_000
    assert quote.total_market_cap == 1_800_000_000_000
    assert normalize_code("sh600519") == "sh600519"
    assert normalize_code("sz000001") == "sz000001"


def test_too_few_fields() -> None:
    assert parse_tencent_quote(b'v_sh600519="1~name~600519";') is None


def test_invalid_price() -> None:
    assert parse_tencent_quote(response(**{"3": "0"})) is None


def test_invalid_market_cap_relationship() -> None:
    assert parse_tencent_quote(response(**{"44": "25000"})) is None


def test_abnormal_volume_ratio() -> None:
    assert parse_tencent_quote(response(**{"49": "100"})) is None


def test_abnormal_turnover_rate() -> None:
    assert parse_tencent_quote(response(**{"38": "100"})) is None
