# Rapport MC-API-CATALOG-001

Date : 20 novembre 2026

Branche : `feat/mc-api-catalog-001`

Base : `main` — `97d81346304b1234b77ae5a8dfe35cb63e787ad6`

## Résultat

Le registre partagé pilote la découverte, la résolution des gestionnaires et la
validation statique. Il décrit 28 commandes API, 12 types d'actions et 6 types
d'événements WebSocket. `api_catalog` conserve le endpoint, l'authentification,
le TTL, l'idempotence, les limites et le port loopback existants.

Les contrats séparent contraintes statiques et préconditions dynamiques. La
disponibilité des moteurs actions et captures est calculée à l'exécution. La
référence `docs/API-REFERENCE.md` est générée depuis le registre et contrôlée par
le test ainsi que par `scripts/generate_api_reference.py --check`.

## Qualification

- Tests ciblés : 10/10 PASS.
- Suite complète : 195/195 PASS en 67,411 s avec le chemin court `MC_TEST_TMP`.
- Première passe diagnostique : 172 PASS et 23 refus historiques
  `WINDOWS_PATH_BUDGET_EXCEEDED` sans chemin court ; relance conforme réussie.
- Authentification : refus HTTP 401 sans bearer, succès avec bearer valide.
- Compatibilité : suite historique complète réussie ; paramètres supplémentaires
  auparavant ignorés toujours tolérés.
- Effets matériels : aucun mouvement, clic, défilement, rapport HID ou capture
  réelle. Tests effectués avec transport simulé et courtier espion.
- Référence générée : à jour.

## Réserves

La qualification porte sur le logiciel et le protocole loopback. Aucun test
matériel n'était requis ni autorisé. La branche ne modifie pas le moteur HID, la
capture, le journal anti-rejeu ou l'installation active. Il n'existe pas de CI
GitHub configurée ; les preuves proviennent de mini-pc-backend.

## Verdict

**PASS** pour MC-API-CATALOG-001. Livraison en PR Draft, sans fusion.
