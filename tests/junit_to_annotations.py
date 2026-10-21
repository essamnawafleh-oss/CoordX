"""Print pytest failures from a JUnit XML file as GitHub error annotations."""
import sys
import xml.etree.ElementTree as ET

for case in ET.parse(sys.argv[1]).iter("testcase"):
    for bad in list(case.findall("failure")) + list(case.findall("error")):
        text = (bad.get("message", "") + "\n" + (bad.text or ""))[-1500:]
        text = text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
        print(f"::error title={case.get('classname')}.{case.get('name')}::{text}")
