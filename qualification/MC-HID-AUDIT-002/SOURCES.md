# Sources primaires

- [Radio.RequestAccessAsync](https://learn.microsoft.com/en-us/uwp/api/windows.devices.radios.radio.requestaccessasync) : lecture toujours permise, autorisation requise pour changer l'état.
- [Radio et RadioState](https://learn.microsoft.com/en-us/uwp/api/windows.devices.radios.radio) : `Off`, `On` et `Disabled`, influence matériel/politique.
- [Radio.SetStateAsync](https://learn.microsoft.com/en-us/uwp/api/windows.devices.radios.radio.setstateasync) : changement asynchrone soumis au consentement, au matériel et aux stratégies.
- [Bluetooth power transitions](https://learn.microsoft.com/en-us/windows-hardware/drivers/bluetooth/bluetooth-core-driver-layer-and-supported-power-transitions) : état radio Off, D3 et réénumération des devnodes.
- [Visual Studio Build Tools workload](https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools) : identifiants VCTools, MSVC et Windows 11 SDK 26100.
- [C++/WinRT desktop](https://learn.microsoft.com/en-us/windows/apps/develop/cpp-winrt/get-started) : application Desktop C++/WinRT et SDK Windows pris en charge.

Consultées le 19 novembre 2026. Les sources expliquent les API ; les verdicts
machine proviennent exclusivement des diagnostics locaux expurgés.
