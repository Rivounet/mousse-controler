# Sources techniques primaires

- [Microsoft — GATT server](https://learn.microsoft.com/en-us/windows/apps/develop/devices-sensors/gatt-server) : fournisseur, caractéristiques, CCCD, publicité et services réservés.
- [Microsoft — CreateDescriptorAsync](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.genericattributeprofile.gattlocalcharacteristic.createdescriptorasync) : création de descripteur local.
- [Microsoft — GattLocalCharacteristicParameters](https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.genericattributeprofile.gattlocalcharacteristicparameters) : propriétés et niveaux de protection.
- [Microsoft — Bluetooth developer FAQ](https://learn.microsoft.com/en-us/windows/apps/develop/devices-sensors/bluetooth-dev-faq) : rôle périphérique dépendant du matériel et disponibilité Win32.
- [Bluetooth SIG — HOGP 1.2](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/hogp_v1-2_1777405843/HOGP_v1.2/out/en/index-en.html) : services obligatoires, rapports, chiffrement et bonding.
- [Microsoft — Bluetooth support in Windows](https://learn.microsoft.com/en-us/windows-hardware/drivers/bluetooth/general-bluetooth-support-in-windows) et [HID transports](https://learn.microsoft.com/en-us/windows-hardware/drivers/hid/hid-transports) : support Host/HOGP Windows.
- [Microsoft — GetCursorPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getcursorpos) : coordonnées écran, station de fenêtres et input desktop.
- [Microsoft — virtual screen](https://learn.microsoft.com/en-us/windows/win32/gdi/the-virtual-screen) et [multiple-monitor metrics](https://learn.microsoft.com/en-us/windows/desktop/gdi/multiple-monitor-system-metrics) : origine et coordonnées négatives.
- [Microsoft — DPI awareness contexts](https://learn.microsoft.com/en-us/windows/win32/hidpi/dpi-awareness-context) et [default DPI awareness](https://learn.microsoft.com/en-gb/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process) : manifeste et Per-Monitor-V2.
- [Microsoft — MOUSEINPUT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput) et [SystemParametersInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-systemparametersinfoa) : accélération et paramètres pointeur.
- [Microsoft — Raw Input](https://learn.microsoft.com/en-us/windows/win32/inputdev/about-raw-input) : distinction des périphériques sources.
- [Microsoft — WM_WTSSESSION_CHANGE](https://learn.microsoft.com/en-us/windows/win32/termserv/wm-wtssession-change), [WTSRegisterSessionNotification](https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsregistersessionnotification) et [WTSGetActiveConsoleSessionId](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-wtsgetactiveconsolesessionid) : verrouillage, changement et session console.
- [Microsoft — CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata) : protection DPAPI liée par défaut à l'utilisateur et à la machine.
- [Microsoft — validation du certificat serveur](https://learn.microsoft.com/en-us/dotnet/api/system.net.servicepointmanager.servercertificatevalidationcallback?view=netframework-4.8.1) : validation personnalisée disponible sous .NET Framework 4.8.

Consultées le 19 novembre 2026. Les conclusions spécifiques aux deux machines
restent fondées sur les preuves locales, pas sur la seule documentation.
