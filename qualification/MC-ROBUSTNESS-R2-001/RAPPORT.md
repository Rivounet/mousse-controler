# MC-ROBUSTNESS-R2-001 — rapport de qualification

Date : 20 novembre 2026

Base obligatoire : `5b158a68325154be0621fd8764fb3d09b6d2e398`

Branche : `fix/mc-robustness-r2-001`

## Verdict

**PASS_WITH_RESERVATIONS** pour la qualification logicielle R2.

C-01 et C-04 sont corrigés dans les doubles et processus isolés. Aucun moteur
HOGP de production, radio, rapport HID, certificat de production, capture ou
cible distante n'a été sollicité.

## C-01 — transport HOGP et WinRT

- trois workers au plus par processus drainent `stdout`/`stderr` et bornent les
  écritures `stdin` ;
- une seule deadline couvre verrou, écriture et réponse ;
- tout timeout ou canal corrompu passe en `invalid`, interdit sa réutilisation
  et déclenche `terminate`, puis `kill`, sans passer par le protocole bloqué ;
- l'arrêt concurrent est sérialisé et borné ;
- `recovery_status()` expose état, raison, code de sortie, lignes `stderr`
  drainées, workers restants et besoin de récupération ;
- si la terminaison OS échoue, le handle reste conservé et un nouveau
  démarrage est refusé ;
- le moteur PowerShell borne chaque opération WinRT et tente `Cancel()` ;
- `StartAdvertising`/`StopAdvertising`, synchrones côté WinRT, restent
  confinés par la deadline de commande Python et la terminaison externe ;
- une transition bouton expirée reste `UNKNOWN`, place R1 en quarantaine,
  publie `release_confirmed=false` et n'est jamais rejouée.

## C-04 — serveur HTTPS LAN

- 8 connexions actives maximum et backlog de 8 par défaut ;
- admission avant création du thread handler et avant authentification métier ;
- deadlines distinctes pour TLS, en-têtes, corps et écriture ;
- lecture exacte de `Content-Length` ; un corps tronqué n'atteint jamais
  `PositionReceiver` ni HMAC ;
- les déconnexions et écritures interrompues libèrent leur slot ;
- un client sain est servi après expiration ou refus d'un client fautif ;
- TLS 1.2 minimum, HMAC, anti-rejeu, ports et interfaces restent inchangés.

## Limites retenues

| Phase | Valeur par défaut | Configuration |
|---|---:|---|
| Démarrage HOGP | 15 s | `hogp_startup_timeout_seconds` |
| Commande HOGP | 3 s | `hogp_command_timeout_seconds` |
| Arrêt protocolaire HOGP | 3 s | `hogp_stop_timeout_seconds` |
| Terminaison processus | 2 s au total | `hogp_termination_timeout_seconds` |
| Opération WinRT | 5 s | constante bornée du moteur |
| Connexions LAN actives | 8 | `position_max_connections` |
| Backlog LAN | 8 | `position_request_queue_size` |
| Handshake TLS | 3 s | `position_tls_handshake_timeout_seconds` |
| En-têtes HTTP | 2 s | `position_header_timeout_seconds` |
| Corps HTTP | 5 s d'inactivité socket | `position_body_timeout_seconds` |
| Écriture HTTP | 2 s | `position_write_timeout_seconds` |

Les valeurs sont validées positives. La limite du corps est une limite
d'inactivité par opération socket, afin de ne pas refuser une capture autorisée
de 24 Mio qui progresse normalement.
Les configurations ne peuvent pas neutraliser les bornes : démarrage HOGP
maximum 60 s, autres bornes HOGP maximum 10 s, timeouts LAN maximum 60 s,
connexions et backlog maximum 64.

## Non-régression R1

Les tests conservent : quarantaine des boutons incertains, arrêt global des
deux moteurs, fermeture durable de la file, `UNKNOWN`,
`release_confirmed=false` et anti-rejeu persistant.

## Réserves

1. `Cancel()` WinRT est best-effort : le confinement fiable reste la deadline
   Python suivie de la terminaison du processus hébergeant WinRT.
2. Les simulations ne prouvent ni la latence réelle WinRT/Schannel ni la
   réception physique d'un rapport de relâchement Bluetooth.
3. Une terminaison OS refusée impose une intervention de récupération ; le code
   la rend observable et interdit un second moteur, sans prétendre la résoudre.
4. Aucune qualification matérielle ni production n'a été réalisée.

## Rollback

Le rollback Git consiste à revenir au parent du commit R2. Aucun état de
production, appairage, certificat, pare-feu ou configuration active n'a été
modifié.
