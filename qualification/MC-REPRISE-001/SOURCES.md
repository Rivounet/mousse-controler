# Sources techniques de qualification

Sources officielles consultées le 19 novembre 2026 :

- [Bluetooth GATT Server — Microsoft Learn](https://learn.microsoft.com/en-us/windows/apps/develop/devices-sensors/gatt-server)
- [BluetoothAdapter.IsPeripheralRoleSupported — Microsoft Learn](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothadapter.isperipheralrolesupported)
- [Bluetooth version and profile support in Windows 11 — Microsoft Learn](https://learn.microsoft.com/en-us/windows-hardware/drivers/bluetooth/general-bluetooth-support-in-windows)
- [HID transport overview — Microsoft Learn](https://learn.microsoft.com/en-us/windows-hardware/drivers/hid/hid-transports)
- [HID over GATT Profile 1.2 — Bluetooth SIG](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/hogp_v1-2_1777405843/HOGP_v1.2/out/en/index-en.html)

Lecture retenue : Windows expose un serveur GATT et le rôle périphérique lorsque
le matériel les prend en charge. HOGP exige cependant une hiérarchie HID
conforme, un Report Map, des notifications, un lien chiffré et le bonding. La
présence des API ne démontre donc pas que le PC cible reconnaîtra cette machine
comme souris.
