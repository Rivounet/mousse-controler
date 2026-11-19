# Décisions structurelles

## Déjà validées

| Sujet | État | Effet |
|---|---|---|
| Deux canaux distincts : HOGP commande, LAN retour | validé par le mandat ; journalisé D-028 | aucune commande souris par le LAN cible |
| Développement/exécution sur mini-pc-backend | D-024 | Git et composants principaux restent sur le mini-PC |
| Pas d'analyse écran ni contrôle intelligent | validé | l'agent ne publie que curseur/topologie/session |
| Pas de fusion ou opération matérielle implicite | D-010/D-023 | portes d'autorisation explicites |

Le texte du mandat attribue les deux canaux à D-024. Le journal historique
D-024 ne contient pas cette décision et qualifiait la cible de « uniquement
HID ». Il n'est pas réécrit : D-028 enregistre la nouvelle décision et amende
explicitement D-004/D-024 sur ce seul point.

## Recommandations techniques

### R1 — Moteur HOGP C++/WinRT

- **Options :** C++/WinRT ; C# WinRT ; PowerShell/Python.
- **Recommandation :** C++/WinRT avec MSVC/Windows SDK.
- **Pourquoi :** surface Microsoft native, binaire autonome, cycle de vie et
  buffers explicites.
- **Risque/dépendance :** chaîne absente ; installation autorisée et build
  reproductible requis.
- **Validation :** compilation, table GATT, chiffrement, pairing, reconnexion et
  1 000 séquences de rapports sans bouton bloqué.

### R2 — Agent C# .NET Framework en session utilisateur

- **Options :** C# Framework 4.8 ; .NET 8 self-contained ; C++ Win32.
- **Recommandation :** C# Framework 4.8 minimal avec manifeste PerMonitorV2.
- **Pourquoi :** runtime inbox probable, P/Invoke direct, UI/notifications de
  session simples, faible dépendance.
- **Risque :** disponibilité exacte à confirmer sur la cible.
- **Validation :** script cible, build local, verrouillage/changement session,
  multi-écrans et DPI.

### R3 — HTTPS épinglé + HMAC

- **Options :** HTTP/HMAC ; HTTPS mutuel ; HTTPS pinning + HMAC.
- **Recommandation :** TLS serveur épinglé et HMAC par agent.
- **Pourquoi :** confidentialité, identité applicative et anti-rejeu sans PKI
  client complexe.
- **Risque :** rotation de certificat/clé ; règle entrante mini-PC éventuelle.
- **Validation :** tests mauvais certificat, signature, séquence, timestamp et
  clé révoquée.

### R4 — Boucle séquentielle à feedback frais

- **Options :** conversion pixel→HID ouverte ; PID continu ; pas proportionnel
  borné avec un feedback par pas.
- **Recommandation :** troisième option, gains coarse/fine configurables.
- **Pourquoi :** stable, testable et robuste à l'accélération variable.
- **Risque :** débit limité par latence.
- **Validation :** matrice positions/DPI/accélération et percentiles publiés.

### R5 — Agent sortant seulement

- **Options :** polling mini-PC vers cible ; WebSocket bidirectionnel ; POST
  sortant cible.
- **Recommandation :** POST HTTPS persistant, latest-only.
- **Pourquoi :** aucun port cible, aucun canal de commande entrant.
- **Risque :** règle entrante sur mini-PC et gestion de backoff.
- **Validation :** coupures LAN, saturation, redémarrage et anti-file.

## Arbitrages utilisateur requis avant exécution

1. autoriser l'installation de MSVC Build Tools/Windows SDK, ou choisir C# avec
   SDK .NET comme moteur HOGP ;
2. autoriser l'activation de la radio, la publicité visible, l'appairage et les
   événements de qualification bornés ;
3. autoriser l'exécution du diagnostic puis l'installation visible de l'agent
   sur MonOrdinateur ;
4. choisir si l'agent démarre manuellement ou au logon ; recommandation : manuel
   pendant la qualification, démarrage au logon seulement après acceptation ;
5. autoriser, si nécessaire, une règle de pare-feu **privée et bornée au port et
   sous-réseau choisis** sur le mini-PC ;
6. décider si la détection par Raw Input est exigée dès le MVP. Recommandation :
   non, sous supervision et arrêt sur trajectoire concurrente ; l'ajouter si les
   tests échouent.
