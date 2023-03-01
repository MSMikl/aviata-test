import pytest

from parsers import parse_a_response, parse_b_response

pytest_plugins = ('pytest_asyncio')


@pytest.mark.asyncio
async def test_parser_a():
    with open('./test_data/response_a.xml', 'r') as file:
        response = file.read()
    parsed_result = await parse_a_response(response)
    assert len(parsed_result) == 223
    segments = []
    for variant in parsed_result:
        for flight in variant['flights']:
            segments += flight['segments']
    assert len(segments) == 598
    for segment in segments:
        assert segment['operating_airline'] is not None
        assert segment['marketing_airline'] is not None
        assert segment['flight_number'] is not None
        assert segment['equipment'] is not None
        assert segment['dep']['at'] is not None
        assert segment['dep']['airport'] is not None
        assert segment['arr']['at'] is not None
        assert segment['arr']['airport'] is not None


@pytest.mark.asyncio
async def test_parser_b():
    with open('./test_data/response_b.xml', 'r') as file:
        response = file.read()
    parsed_result = await parse_b_response(response)
    assert len(parsed_result) == 10
    segments = []
    for variant in parsed_result:
        for flight in variant['flights']:
            segments += flight['segments']
    assert len(segments) == 20
    for segment in segments:
        assert segment['operating_airline'] is not None
        assert segment['marketing_airline'] is not None
        assert segment['flight_number'] is not None
        assert segment['equipment'] is not None
        assert segment['dep']['at'] is not None
        assert segment['dep']['airport'] is not None
        assert segment['arr']['at'] is not None
        assert segment['arr']['airport'] is not None
