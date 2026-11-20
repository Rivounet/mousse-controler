# MC-ROBUSTNESS-R2-001 — rapport de qualification

Date : 21 novembre 2026

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
- handshake TLS déplacé hors du thread d'acceptation, dans le worker déjà
  couvert par le slot ; un client TLS muet ne bloque plus les acceptations ;
- délais d'inactivité et deadlines absolues distinctes pour les en-têtes et
  le corps ; chaque `recv` utilise le plus petit budget restant ;
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
| En-têtes HTTP, inactivité | 2 s | `position_header_timeout_seconds` |
| En-têtes HTTP, total | 5 s | `position_header_total_timeout_seconds` |
| Corps position, inactivité | 5 s | `position_body_timeout_seconds` |
| Corps position, total | 10 s | `position_body_total_timeout_seconds` |
| Corps capture, total | 120 s | `position_capture_body_total_timeout_seconds` |
| Écriture HTTP | 2 s | `position_write_timeout_seconds` |

Les valeurs sont validées positives et les budgets totaux doivent couvrir leur
limite d'inactivité. La capture dispose de 120 s pour 24 Mio, soit un débit
moyen minimal d'environ 205 Kio/s, compatible avec un LAN normal. Un client qui
envoie régulièrement quelques octets ne peut pas repousser cette échéance.
Les configurations ne peuvent pas neutraliser les bornes : démarrage HOGP
maximum 60 s, autres bornes HOGP maximum 10 s, timeouts LAN maximum 60 s,
deadline totale de capture maximum 300 s, connexions et backlog maximum 64.

## Correctif de revue B1/B2

Le test B1 emploie un certificat auto-signé réservé au loopback : une connexion
TCP reste muette avant son `ClientHello`, tandis qu'un second client termine un
vrai handshake TLS et reçoit `202` avant l'expiration du premier. Le premier
expire ensuite et le compteur de slots revient à zéro. Le test couvre la pile
TLS de Python présente sur la machine de qualification, pas Schannel ni le
certificat de production.

Le test B2 envoie en continu des fragments à un intervalle inférieur à la
limite d'inactivité, pour les en-têtes puis le corps. Les deadlines absolues
ferment les deux connexions, aucun corps incomplet n'atteint le récepteur et un
client sain est ensuite accepté. Une capture loopback de 24 Mio est acceptée ;
HMAC et anti-rejeu restent vérifiés par leur test existant.

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
