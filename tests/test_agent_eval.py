from evals.agent_eval import extract_numbers, is_sourced, unsourced


def test_extract_numbers_accepts_pt_br_and_decimal_point() -> None:
    values = [v for v, _ in extract_numbers("13.166,7 m², CA 1,78 e 145 unidades")]
    assert values == [13166.7, 1.78, 145.0]
    assert extract_numbers("13166.7") == [(13166.7, 1)]
    assert extract_numbers("1.427 vagas") == [(1427.0, 0)]


def test_is_sourced_accepts_rounding_by_cited_decimals() -> None:
    assert is_sourced(13166.7, 1, [13166.70000001])
    assert is_sourced(36.4, 1, [36.44])
    assert not is_sourced(37, 0, [36.4])


def test_unsourced_flags_invented_number_and_accepts_question() -> None:
    tools = ['{"total": 2, "area": 13166.73}']
    question = "Qual a área da torre p12?"

    assert unsourced("A torre p12 tem 13.166,7 m².", tools, question) == []
    assert unsourced("São 2 torres e 37 unidades.", tools, question) == ["37"]
