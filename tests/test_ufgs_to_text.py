from scripts.ufgs_to_text import sec_to_lines

SEC = """<?xml version="1.0" encoding="windows-1252"?><SEC><HDR><DTA>UFGS-46 61 00 (May 2021)</DTA></HDR>
<SCN>SECTION 46 61 00</SCN><BRK/><STL>FILTRATION EQUIPMENT</STL><BRK/><DTE>05/21</DTE>
<NTE><NPR>NOTE:  Editor guidance.</NPR></NTE>
<PRT><TTL>PART 1   GENERAL</TTL><BRK/>
<SPT><TTL>REFERENCES</TTL><BRK/><TXT>The publications listed below form a part.</TXT>
<REF><ORG>ASTM INTERNATIONAL (ASTM)</ORG><BRK/><RID>ASTM A36/A36M</RID><RTL>(2019) Carbon Structural Steel</RTL></REF>
</SPT>
<SPT><TTL>SUBMITTALS</TTL><BRK/><TXT>Submit the following in accordance with Section <SRF>01 33 00</SRF>:</TXT>
<LST><SUB>SD-02 Shop Drawings</SUB></LST><ITM><SUB>Filtration System</SUB></ITM><ITM>  Include wiring
diagrams.</ITM>
<SPT><TTL>Certificates</TTL><TXT>Provide <MET>750 liters</MET><ENG>200 gallons</ENG> per minute.</TXT></SPT>
</SPT></PRT>
<PRT><TTL>PART 2   PRODUCTS</TTL><SPT><TTL>Steel Pipe</TTL><OLG><OLI>Bolts:  <RID>ASTM A307</RID>.</OLI></OLG></SPT></PRT>
</SEC>"""


def test_sec_to_lines() -> None:
    assert sec_to_lines(SEC) == [
        "SECTION 46 61 00", "FILTRATION EQUIPMENT", "PART 1 GENERAL", "1.1 REFERENCES",
        "The publications listed below form a part.", "ASTM INTERNATIONAL (ASTM)",
        "ASTM A36/A36M (2019) Carbon Structural Steel", "1.2 SUBMITTALS",
        "Submit the following in accordance with Section 01 33 00:", "SD-02 Shop Drawings", "a. Filtration System",
        "b. Include wiring diagrams.", "1.2.1 Certificates", "Provide 200 gallons per minute.", "PART 2 PRODUCTS",
        "2.1 Steel Pipe", "a. Bolts: ASTM A307.",
    ]
