from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "hogp" / "AppxManifest.xml"
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


if __name__ == "__main__":
    unittest.main()
