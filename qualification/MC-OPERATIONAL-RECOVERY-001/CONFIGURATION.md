# Configuration préparée

## Copie de staging

La configuration active n'a pas été remplacée. Une copie sensible hors Git a
été préparée sous `staging/MC-OPERATIONAL-RECOVERY-001/config/`.

Modifications proposées :

| Paramètre | Valeur préparée |
|---|---|
| `hogp_executable` | `mousse-hogp-packaged.exe` |
| `action_journal` | `runtime/MC-HID-EXEC-001/action-journal.jsonl` |
| registre anti-rejeu | `<action_journal>.ids`, créé par le runtime |
| `capture_directory` | `runtime/MC-HID-EXEC-001/captures` |
| index capture | `<capture_directory>/.capture-index.json` |
| `event_port` | 8767, boucle locale |
| rétention identifiants | 2 592 000 secondes |
| fichier capture maximal | 16 Mio |
| stockage captures maximal | 512 Mio |

## Validations

- JSON lisible ;
- alias MSIX résolu ;
- chemins parents et fichiers TLS référencés présents ;
- blobs DPAPI copiés sans régénération et déchiffrables dans le contexte prévu ;
- configuration originale conservée dans la sauvegarde et le rollback local ;
- aucune valeur sensible publiée.

Cette copie ne doit être promue qu'après signature du nouveau MSIX, inspection
des tâches, nouvelle qualification et autorisation de déploiement.
