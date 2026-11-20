# Diagnostic Bluetooth local

`diagnose.ps1` inventorie en lecture seule l'adaptateur, son pilote, les rôles
BLE déclarés et la présence des API WinRT nécessaires à un serveur GATT.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bluetooth\diagnose.ps1
```

Le script ne crée aucun service GATT, ne démarre aucune publicité, ne tente
aucun appairage et n'émet aucun rapport HID. Un résultat positif démontre les
préconditions Windows, pas la compatibilité HOGP effective.

L'étape suivante est le protocole contrôlé décrit dans
`qualification/MC-REPRISE-001/PROTOCOLE-HID.md`. Elle exige une autorisation
explicite avant exécution.

`manage_pairability.py` ouvre, uniquement après confirmation explicite, une
fenêtre d'appairage bornée en activant les connexions entrantes et la découverte
Bluetooth Windows. Il relève l'état initial et le restaure dans un bloc
`finally`, y compris après interruption :

```powershell
python .\scripts\bluetooth\manage_pairability.py `
  --duration-seconds 120 --confirm-pairing-window
```

Cet outil ne démarre aucun service GATT, n'effectue aucun appairage et ne laisse
pas la découverte activée après la fenêtre demandée.
