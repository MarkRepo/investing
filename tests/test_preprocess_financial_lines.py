from scripts import preprocess_report as pre


def test_extract_financial_line_rows_a_share():
    text = """
    项目                     2025/12/31       2024/12/31
    营业收入               168,838,102.55   147,693,382.69
    营业成本                 59,831,212.11    52,004,113.45
    研发费用                  1,243,567.89     1,134,812.00
    归属于母公司股东的净利润  85,219,487.33    74,734,102.54
    """
    rows = pre.extract_financial_line_rows(text, market="SSE")
    keys = {r["standard_key"] for r in rows}
    assert "revenue" in keys
    assert "cost_of_revenue" in keys
    assert "rd_expense" in keys
    assert "net_income_to_parent" in keys


def test_extract_financial_line_rows_us():
    text = """
    Consolidated Statements of Operations
    (in thousands)                                    2024            2023
    Revenue                                        1,477,056         872,053
    Cost of revenue                                   268,291         169,400
    Research and development                           38,504          27,432
    Net income                                        126,221           5,558
    """
    rows = pre.extract_financial_line_rows(text, market="US")
    keys = {r["standard_key"] for r in rows}
    assert "revenue" in keys
    assert "cost_of_revenue" in keys
    assert "rd_expense" in keys
    assert "net_income" in keys


def test_extract_financial_line_rows_numeric_candidates():
    text = "营业收入  168,838,102.55   147,693,382.69"
    rows = pre.extract_financial_line_rows(text, market="SSE")
    assert len(rows) == 1
    # Candidates should hold BOTH year columns (caller picks fiscal_year)
    assert len(rows[0]["numeric_candidates"]) == 2
    assert 168838102.55 in rows[0]["numeric_candidates"]


def test_extract_financial_line_rows_unknown_label_skipped():
    text = "不存在的科目名  100   200"
    rows = pre.extract_financial_line_rows(text, market="SSE")
    assert rows == []
