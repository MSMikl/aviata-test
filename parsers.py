import asyncio
import json
import lxml.etree

from collections import defaultdict
from datetime import datetime


async def parse_a_response(response: str) -> list[dict]:

    namespaces = {
        'a': "http://schemas.datacontract.org/2004/07/SiteCity.Avia.Search",
        'b': "http://schemas.datacontract.org/2004/07/SiteCity.Avia.Common.Avia",
    }

    def find_text_or_default(
        element: lxml.etree.Element,
        query: str,
        namespaces: dict = namespaces,
        default=None
    ) -> str:
        result = element.xpath(query, namespaces=namespaces)
        if not result:
            return default
        try:
            text = result[0].text
        except AttributeError:
            return default
        return text

    tree = lxml.etree.fromstring(response)
    result = []
    variants = tree.xpath('.//a:FlightData/a:FlightData', namespaces=namespaces)
    for variant in variants:
        variant_data = {}
        flights_numbered = defaultdict(dict)
        segments = variant.findall('.//b:Segments/b:OfferSegment', namespaces=namespaces)
        for segment in segments:
            segment_data = {}
            segment_data['equipment'] = find_text_or_default(segment, './/b:AirCraft')
            segment_data['operating_airline'] = find_text_or_default(segment, './/b:OperatingAirline')
            segment_data['marketing_airline'] = find_text_or_default(segment, './/b:MarketingAirline')
            segment_data['flight_number'] = find_text_or_default(segment, './/b:FlightNum', default='').replace(f"{segment_data['marketing_airline']}-", '')
            if find_text_or_default(segment, './/b:Baggage/b:BaggageType') == 'Pieces':
                num_pieces = find_text_or_default(segment, './/b:Baggage/b:Count')
                segment_data['baggage'] = f'{num_pieces}PC'
            else:
                segment_data['baggage'] = None
            segment_data['dep'] = {
                'airport': find_text_or_default(segment, './/b:Departure/b:Iata'),
                'at': datetime.strptime(
                    find_text_or_default(segment, './/b:Departure/b:Date'),
                    '%d.%m.%Y %H:%M',
                )
            }
            segment_data['arr'] = {
                'airport': find_text_or_default(segment, './/b:Arrival/b:Iata'),
                'at': datetime.strptime(
                    find_text_or_default(segment, './/b:Arrival/b:Date'),
                    '%d.%m.%Y %H:%M',
                )
            }
            rph = find_text_or_default(segment, './/b:Rph', default=1)
            flights_numbered[rph]['segments'] = flights_numbered[rph].get('segments', [])
            flights_numbered[rph]['segments'].append(segment_data)

        flights = list(flights_numbered.values())
        for flight in flights:
            flight['segments'].sort(key=lambda x: x['dep']['at'])
            flight['duration'] = int((flight['segments'][-1]['arr']['at'] - flight['segments'][0]['dep']['at']).total_seconds())
        
        variant_data['flights'] = flights
        variant_data['refundable'] = False
        variant_data['validating_airline'] = find_text_or_default(variant, ".//b:ValidatingAirline")
        variant_data['pricing'] = {
            'currency': 'EUR',
            'total': f'{float(find_text_or_default(variant, f".//a:AdultPrice")):.2f}',
            'base': f'{float(find_text_or_default(variant, f".//a:AdultPrice")):.2f}',
            'taxes': "0.00"
        }
        result.append(variant_data)
    return result


async def parse_b_response(response: str) -> list[dict]:

    def get_first_element_or_none(tree: lxml.etree.ElementTree, query: str) -> lxml.etree.Element:
        elements = tree.xpath(f'.//*[contains(local-name(), "{query}")]')
        if elements:
            return elements[0]
        return lxml.etree.Element('empty')

    tree = lxml.etree.fromstring(response).xpath('.//*[contains(local-name(), "Body")]')[0]

    result = []
    with open('aircrafts.json', 'r') as file:
        aircrafts = json.load(file)
    variants = tree.xpath('.//*[contains(local-name(), "PricedItinerary")]')
    for variant in variants:
        variant_data = {
            'flights': [],
            'refundable': False,
            'validating_airline': None,
        }
        validating_carrier_element = variant.xpath('.//*[contains(local-name(), "ValidatingCarrier")]/*[contains(local-name(), "Default")]')
        if validating_carrier_element:
            variant_data['validating_airline'] = validating_carrier_element[0].get('Code')
        flights = variant.xpath('.//*[contains(local-name(), "FlightSegment")]')
        baggage_elements = variant.xpath('.//*[contains(local-name(), "BaggageInformation")]')
        baggage = {
            get_first_element_or_none(baggage_element, 'Segment').get('Id'): get_first_element_or_none(baggage_element, 'Allowance').get('Pieces')
            for baggage_element in baggage_elements
        }
        for number, flight in enumerate(flights):
            flight_data = {}
            segment_data = {}
            operating_airline = get_first_element_or_none(flight, "OperatingAirline")
            segment_data['operating_airline'] = operating_airline.get('Code')
            segment_data['flight_number'] = operating_airline.get('FlightNumber')
            segment_data['marketing_airline'] = get_first_element_or_none(flight, "MarketingAirline").get('Code')
            equipment = get_first_element_or_none(flight, "Equipment").get('AirEquipType')
            segment_data['equipment'] = aircrafts.get(equipment)
            segment_data['dep'] = {
                'at': datetime.strptime(flight.get('DepartureDateTime'), '%Y-%m-%dT%H:%M:%S'),
                'airport': get_first_element_or_none(flight, "DepartureAirport").get('LocationCode'),
            }
            segment_data['arr'] = {
                'at': datetime.strptime(flight.get('ArrivalDateTime'), '%Y-%m-%dT%H:%M:%S'),
                'airport': get_first_element_or_none(flight, "ArrivalAirport").get('LocationCode'),
            }
            segment_baggage = baggage.get(str(number))
            if segment_baggage == '0':
                segment_data['baggage'] = None
            else:
                segment_data['baggage'] = f"{segment_baggage}PC"
            flight_data['segments'] = [segment_data]
            flight_data['duration'] = int((flight_data['segments'][-1]['arr']['at'] - flight_data['segments'][0]['dep']['at']).total_seconds())
            variant_data['flights'].append(flight_data)

        pricing_element = get_first_element_or_none(variant, 'ItinTotalFare')
        if len(pricing_element):
            total_element = get_first_element_or_none(pricing_element, 'TotalFare')
            taxes_element = get_first_element_or_none(pricing_element, 'Taxes')
            pricing_data = {
                'total': f"{float(total_element.get('Amount')):.2f}",
                'currency': total_element.get('CurrencyCode'),
                'base': f"{float(get_first_element_or_none(pricing_element, 'BaseFare').get('Amount')):.2f}",
                'taxes': f"{float(get_first_element_or_none(taxes_element, 'Tax').get('Amount')):.2f}",
            }
        else:
            pricing_data = {}
        variant_data['pricing'] = pricing_data
        result.append(variant_data)
    return result


if __name__ == "__main__":
    with open('./providers/response_a.xml', 'r') as file:
        response = file.read()
    asyncio.run(parse_a_response(response))
