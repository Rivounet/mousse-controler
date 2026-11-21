# Risques résiduels

| Risque | Niveau | État | Condition de levée |
|---|---|---|---|
| nouveau MSIX non signé | `BLOCKER` | clé privée de signature absente | fournir le certificat approuvé, signer et vérifier |
| tâches planifiées non inspectées | `MAJOR` | accès refusé dans le contexte actuel | inspection passive autorisée avant installation |
| PositionAgent cible inconnu | `MAJOR` | SSH sandbox refusé | inspection cible sous accès déjà approuvé ou nouveau mandat |
| configuration active encore C++ | `MAJOR` | volontairement inchangée | promotion atomique sous mandat de déploiement |
| persistances modernes absentes | `MAJOR` | chemins préparés, non initialisés | activation qualifiée avec sauvegarde et contrôle de santé |
| correctifs R1–R5 non requalifiés matériellement | `MAJOR` | qualification locale seulement | mandat matériel distinct |
| builds non reproductibles bit-à-bit | `MINOR` | SHA propres à chaque build | manifester et vérifier chaque artefact |

## Réserves conservées

- annulation WinRT best-effort ;
- libération physique incertaine après rupture de transport ;
- quota capture non transactionnel entre processus indépendants ;
- roulette horizontale absente ;
- sept diagnostics matériels exclus ;
- aucune activation, installation ou qualification réelle effectuée ici.

Le blocage de signature suffit à maintenir le verdict **PARTIAL**. Il ne bloque
pas la conservation des sauvegardes, du worktree qualifié ou de la configuration
préparée.
