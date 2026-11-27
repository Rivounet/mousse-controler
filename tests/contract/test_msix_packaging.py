from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "packaging" / "hogp" / "AppxManifest.xml"
QUALIFICATION_MANIFEST = (
    ROOT / "packaging" / "hogp-qualification" / "AppxManifest.xml"
)
FOUNDATION = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
DESKTOP = "http://schemas.microsoft.com/appx/manifest/desktop/windows10"
INSTALLED_BASELINE_VERSION = (1, 0, 0, 2)


class MsixPackagingTests(unittest.TestCase):
    def test_package_identity_advances_installed_baseline(self):
        root = ET.parse(MANIFEST).getroot()
        identity = root.find(f"{{{FOUNDATION}}}Identity")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.attrib["Name"], "Rivounet.MousseControler.Hogp")
        self.assertEqual(identity.attrib["Publisher"], "CN=MousseControler")
        self.assertEqual(identity.attrib["ProcessorArchitecture"], "x64")
        version = tuple(int(part) for part in identity.attrib["Version"].split("."))
        self.assertEqual(len(version), 4)
        self.assertGreater(version, INSTALLED_BASELINE_VERSION)

    def test_package_keeps_powershell_host_and_execution_alias(self):
        root = ET.parse(MANIFEST).getroot()
        application = root.find(f".//{{{FOUNDATION}}}Application")
        self.assertIsNotNone(application)
        assert application is not None
        self.assertEqual(application.attrib["Executable"], "powershell.exe")
        aliases = root.findall(f".//{{{DESKTOP}}}ExecutionAlias")
        self.assertEqual([item.attrib["Alias"] for item in aliases],
                         ["mousse-hogp-packaged.exe"])

    def test_qualification_package_has_a_distinct_identity_and_alias(self):
        production = ET.parse(MANIFEST).getroot()
        qualification = ET.parse(QUALIFICATION_MANIFEST).getroot()
        production_identity = production.find(f"{{{FOUNDATION}}}Identity")
        qualification_identity = qualification.find(f"{{{FOUNDATION}}}Identity")
        assert production_identity is not None
        assert qualification_identity is not None
        self.assertNotEqual(
            production_identity.attrib["Name"],
            qualification_identity.attrib["Name"],
        )
        self.assertEqual(
            qualification_identity.attrib["Name"],
            "Rivounet.MousseControler.Hogp.Qualification",
        )
        aliases = qualification.findall(f".//{{{DESKTOP}}}ExecutionAlias")
        self.assertEqual(
            [item.attrib["Alias"] for item in aliases],
            ["mousse-hogp-qualification.exe"],
        )
        self.assertNotEqual(
            aliases[0].attrib["Alias"], "mousse-hogp-packaged.exe")

    def test_build_script_selects_the_qualification_manifest_explicitly(self):
        source = (ROOT / "scripts" / "build" / "Build-HogpPackage.ps1").read_text(
            encoding="utf-8")
        self.assertIn("[switch]$Qualification", source)
        self.assertIn("packaging\\hogp-qualification\\AppxManifest.xml", source)
        self.assertIn("MousseControler.Hogp.Qualification.msix", source)


if __name__ == "__main__":
    unittest.main()
