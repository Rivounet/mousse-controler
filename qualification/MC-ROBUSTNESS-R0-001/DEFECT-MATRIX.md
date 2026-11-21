# Matrice de caractérisation et de défauts

Les tests `current_defect` sont une suite de caractérisation non bloquante : un
PASS signifie que le défaut de référence a été reproduit de manière
déterministe. Il ne signifie pas que le futur contrat est satisfait. Chaque
ligne ci-dessous distingue donc le comportement courant du critère futur.

| ID | Situation | Comportement courant figé | Attendu futur | Lot | Reproduction |
|---|---|---|---|---|---|
| T01 / C-01 | moteur HOGP vivant mais muet | `startup_timeout` n'interrompt pas `readline()` | deadline bornée et arrêt hors canal bloqué | R2 | `test_T01_current_defect_alive_silent_engine_ignores_startup_timeout` |
| T02 | réponse HOGP incomplète | rejet `TransportError`, sans replay | rejet borné, diagnostic précis, état incertain si effet possible | R2 | `test_T02_incomplete_engine_response_fails_closed` |
| T03 | processus HOGP interrompu | la lecture directe expose le code de sortie | toutes les commandes/fermetures terminent dans une borne | R2 | `test_T03_interrupted_engine_reports_exit_code` |
| T04 / C-01 | `stderr` saturé | aucun lecteur `stderr`; processus/lecture peuvent rester bloqués | drainage borné sans fuite de secrets ni deadlock | R2 | `test_T04_current_defect_saturated_stderr_is_never_drained` |
| A01 / C-02 | transition bouton ambiguë + `continue` | action `UNKNOWN`, contrôleur actif, masque simulé à 1 | quarantaine/arrêt fail-safe, aucune action suivante | R1 | `test_A01_current_defect_ambiguous_press_continue_leaves_pressed_state` |
| A02 | action non idempotente incertaine | `UNKNOWN`, un seul mouvement simulé malgré `retry` | conserver zéro rejeu automatique ambigu | R1 | `test_A02_uncertain_non_idempotent_move_is_not_replayed` |
| A03 | arrêt pendant action suspendue | réveil, annulation, arrêt et aucun HID simulé ultérieur | conserver la propriété pour tous états/actions | R1 | `test_A03_emergency_stop_releases_suspended_wait` |
| A04 / C-06 | `close()` avec file non vide | action courante `CANCELLED`, action en file reste `ACCEPTED` | toutes les entrées terminent durablement | R1 | `test_A04_current_defect_close_leaves_queued_action_accepted` |
| A05 / C-05 | arrêt global + séquence historique | l'exécuteur moderne est arrêté, `SequenceRunner.stop()` omis | arrêter les deux moteurs, HID prioritaire | R1 | `test_A05_current_defect_global_stop_omits_historical_sequence` |
| N01 / C-04 | client HTTPS lent | un corps partiel attend sans deadline explicite | timeout lecture/handshake mesuré, reprise propre | R2 | `test_N01_current_defect_slow_client_has_no_read_deadline` |
| N02 / C-04 | corps HTTP tronqué | le handler passe les octets reçus sans vérifier leur nombre | refuser le corps incomplet avant authentification métier | R2 | `test_N02_current_defect_incomplete_body_is_accepted_by_handler` |
| N03 / C-04 | connexions simultanées | quatre handlers simultanés acceptés, sans plafond actif explicite | plafond documenté, refus/reprise bornés | R2 | `test_N03_threaded_handler_accepts_simultaneous_connections` |
| S01 / C-03 | quota atteint + suppression refusée | corrigé : admission refusée avant PNG et pic complet sous quota | admission avant écriture et quota dur incluant temporaires | R3 | `test_S01_quota_pressure_retains_undeletable_file_as_error` |
| S02 | suppression refusée | `DELETE_FAILED` persiste, fichier traçable et suppression rejouable | conserver cette propriété pendant le durcissement quota | R3 | `test_S02_delete_denied_survives_restart_and_can_be_retried` |
| S03 | redémarrage avec capture incomplète | entrée récupérée en `FAILED` explicite | conserver suivi et fichier éventuel, aucune perte silencieuse | R3 | `test_S03_restart_marks_incomplete_capture_failed` |
| L01 / C-07 | échec de création du second serveur | corrigé : tous les serveurs créés sont fermés en ordre inverse | rollback inverse complet de toutes les ressources | R3 | `test_L01_partial_server_creation_is_closed` |
| L02 / C-07 | échec pendant la fermeture | corrigé : les fermetures suivantes continuent et les erreurs sont agrégées | fermeture best-effort complète puis erreur agrégée | R3 | `test_L02_close_failure_does_not_skip_remaining_cleanup` |
| L03 / C-08 | échec mise à jour/rollback | corrigé : le script réel restaure, ou persiste `RECOVERY_REQUIRED` après deux essais | transaction testée avec restauration bornée et état de récupération explicite | R3 | `test_L03_failed_update_restores_previous_content_with_real_script` |

## Propriétés de non-régression

1. Une action non idempotente dont l'effet est incertain n'est jamais rejouée
   automatiquement.
2. Un arrêt réveille les actions suspendues et interdit tout nouveau rapport
   simulé après la publication de l'arrêt.
3. Une suppression refusée ne produit jamais l'état `DELETED`; le fichier et
   `storage_path` restent traçables après redémarrage.
4. Une capture incomplète au redémarrage devient une erreur explicite.
5. Les réponses HOGP invalides ou un processus interrompu échouent fermées.
6. Les tests R0 n'appellent jamais le transport natif, la capture d'écran, la
   radio, la session cible, SSH ou les tâches planifiées.
7. Tous les fichiers temporaires sont confinés à des répertoires temporaires ;
   aucune donnée de production n'est lue ou modifiée.

## Limites des doubles

- Les tests réseau utilisent HTTP loopback éphémère, pas une négociation TLS :
  ils caractérisent la lecture du handler, pas Schannel, le certificat ou HMAC.
- Le processus HOGP est un faux flux Python : saturation et silence sont
  déterministes, mais la taille réelle des pipes Windows et WinRT ne sont pas
  mesurées.
- `SimulatedHidTransport` ne prouve ni livraison Bluetooth ni libération réelle
  d'un bouton ; il prouve seulement l'ordonnancement logiciel.
- Les scénarios de stockage utilisent un système de fichiers temporaire et une
  injection `PermissionError`, pas un disque plein, antivirus ou panne secteur.
- L03 et les tests R3 exécutent le script réel sur des fichiers temporaires,
  mais remplacent les cmdlets de tâche/processus par un harness isolé. Ils
  qualifient la transaction de fichiers et ses états, pas une tâche Windows
  réelle ni les droits de la session cible.
- Les serveurs de cycle de vie sont des doubles : ils prouvent les appels omis,
  pas la libération effective d'un socket Windows réel.
