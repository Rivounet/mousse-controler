# MC-ROBUSTNESS-R2-001 — décisions techniques

## D-R2-01 — workers de pipe bornés par processus

Windows ne fournit pas un `select()` portable sur les pipes de `Popen`. Un
worker fixe par flux permet au thread appelant d'attendre une `Queue` avec
deadline. Il n'existe ni thread par commande ni croissance dynamique : trois
workers par moteur, joints dans la borne de terminaison.

## D-R2-02 — deadline unique par commande

La même échéance couvre attente du verrou, écriture et lecture de tous les
événements jusqu'à la réponse attendue. Une succession d'événements ne peut
donc pas renouveler indéfiniment le budget.

## D-R2-03 — invalidation avant terminaison

Le canal est détaché avant `terminate`/`kill`. Aucune commande suivante ne peut
l'utiliser. La terminaison emprunte le handle OS, pas `stdin`, et ne dépend ni
du verrou de commande ni d'une réponse du moteur.

## D-R2-04 — conserver le handle en cas d'échec OS

Un processus que l'OS refuse de terminer reste référencé comme canal échoué.
`recovery_required=true` et tout nouveau `start()` retente le confinement puis
refuse de créer un second moteur. Ceci évite un processus orphelin silencieux.

## D-R2-05 — WinRT borné et confinement processus

Chaque `IAsyncOperation` attend au plus 5 s et reçoit `Cancel()` au timeout.
Comme WinRT ne garantit pas que l'annulation interrompt le travail natif, la
borne Python reste l'autorité externe et termine le processus hébergeant.
Les appels synchrones de publicité ne peuvent pas recevoir un jeton
d'annulation ; ils sont donc bornés par cette même supervision externe.

## D-R2-06 — admission LAN avant thread, handshake dans le worker

Le sémaphore est acquis après `accept()` et avant la création du worker. Un
client excédentaire est fermé sans thread ni authentification. Le handshake TLS
est ensuite exécuté par ce worker admis, jamais par le thread unique
d'acceptation. Son échec ferme la socket enveloppée et libère le slot par le
même chemin que le handler. Le nombre de handshakes et de threads concurrents
reste donc limité par `max_connections`. Le backlog est configuré avant
`listen()`, contrairement à l'affectation tardive historique.

## D-R2-07 — inactivité et deadline absolue par phase

TLS, en-têtes, corps et écriture ont des budgets distincts. Pour les lectures,
le timeout socket limite l'inactivité et une échéance monotone limite la durée
totale. Avant chaque `recv`, le timeout effectif devient le minimum entre les
deux budgets ; aucun fragment ne réinitialise l'échéance totale. La position a
10 s au total et la capture 120 s, ce qui accepte 24 Mio à environ 205 Kio/s.
La lecture exacte précède HMAC et l'anti-rejeu.
