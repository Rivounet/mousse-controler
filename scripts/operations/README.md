# Procédures d'exploitation Codex

Ces procédures sont les points d'entrée qualifiés pour le mini-PC Windows. Elles
produisent du JSON, n'exposent ni compte, ni adresse, ni clé, et utilisent les
codes communs suivants : `0` = objectif atteint, `1` = défaut constaté,
`2` = précondition ou autorisation manquante, `130` = interruption.

| Procédure | Contexte et effets autorisés | Limites |
|---|---|---|
| `Check-CodexEnvironment.ps1` | Sandbox; lecture des outils, fichiers et Git | Ne teste pas le réseau |
| `Inspect-LocalRuntime.ps1` | Contexte Windows approuvé; lecture de la tâche et des processus | Aucun démarrage, ACL ou élévation |
| `Inspect-RemoteTarget.ps1` | Hors sandbox, canal SSH exact; commande distante passive | Session 0, aucune preuve d'affichage |
| `Invoke-BuildAndQualify.ps1` | Sandbox; écrit seulement sous `out/qualification` | Exclut tout matériel et déploiement |
| `Prepare-MsixSigning.ps1` | Contexte Windows approuvé; crée ou lit une clé utilisateur protégée | N'installe jamais la confiance ni le paquet |
| `Prepare-Deployment.ps1` | Sandbox; contrôle passif des preuves et artefacts | Ne déploie et n'active rien |

## Contextes approuvés

Le canal distant est exclusivement :

```text
C:\Windows\System32\OpenSSH\ssh.exe -F %USERPROFILE%\.ssh\monordinateur-pv-mig.conf MonOrdinateur
```

Codex doit demander directement l'exécution hors sandbox avec cette liste
d'arguments exacte. La règle persistante est limitée au binaire, au fichier de
configuration et à l'alias. La configuration impose la vérification stricte de
l'hôte et conserve la clé hors du dépôt.

La lecture dynamique de la tâche locale utilise exclusivement :

```text
C:\Windows\System32\schtasks.exe /Query /TN \MousseControler-HOGP
```

Les scripts d'inspection peuvent nécessiter une approbation limitée à leur
chemin exact. Une erreur `access denied` depuis la sandbox signifie seulement
que le fournisseur système y est masqué; elle ne justifie ni ACL supplémentaire,
ni tâche auxiliaire, ni administrateur.

## Contrats et reprise

Chaque script est idempotent dans son mode de lecture. Une interruption ne doit
laisser aucun processus auxiliaire. `Prepare-MsixSigning.ps1 -Action Create`
supprime certificat et dossier s'il échoue avant la publication des métadonnées.
Un second `Create` retourne l'état existant sans remplacer la clé. L'action
`Restore` déchiffre le secret DPAPI et réimporte le PFX uniquement dans
`CurrentUser\My`; elle ne touche à aucun magasin de confiance.

La séquence normale est : environnement, inspections locale et distante, build
et qualification, préparation de signature, puis préparation du déploiement.
L'installation du certificat public dans `TrustedPeople`, le remplacement du
MSIX et l'activation sont des opérations séparées soumises à autorisation.

## Autorisation opérationnelle active (21 novembre 2026)

L'utilisateur autorise sur les deux machines nommées la confiance du **certificat public MSIX v2 vérifié**, l'installation du MSIX signé, la mise à jour transactionnelle de PositionAgent, la synchronisation contrôlée du runtime et des tâches/configurations Mousse-controler, puis l'activation et les contrôles de santé **sans commande HID ni capture**. Le mandat reste limité aux composants Mousse-controler et ne permet ni désactivation de protections Windows, ni permissions générales, ni fusion de PR.

La séquence d'exploitation est : `Check-CodexEnvironment` → `Inspect-LocalRuntime` et `Inspect-RemoteTarget` dans leurs contextes exacts → `Invoke-BuildAndQualify -Profile full-local` → `Prepare-MsixSigning -Action Status/Qualify` → `Prepare-Deployment` → sauvegarde immédiate et préflight → **installation autorisée** de la confiance et du MSIX signé → mise à jour PositionAgent avec `Plan` puis `Install` → promotion atomique de la configuration et réinscription de la tâche → activation progressive → contrôles santé, API/WebSocket, authentification, processus, sessions, ports et persistances → rapport et rollback prêt.

**Attention :** `Prepare-Deployment.ps1` reste volontairement un contrôle passif et peut renvoyer `PREPARED_NOT_AUTHORIZED` parce que ses champs d'autorisation sont statiques ; cela ne révoque pas l'autorisation utilisateur explicite, mais ce script **ne réalise aucune installation**. Vérifier l'autorisation et les empreintes réelles séparément avant les opérations mutantes. Ne pas confondre le certificat privé de signature (`CurrentUser\\My`) et le certificat **public** à approuver dans le magasin adapté. Revalider signature/chaîne, identité, version et SHA de l'artefact réellement installé. Préserver l'ancien package et son certificat jusqu'à la qualification de la transition.

L'état `OPERATIONAL_PASS` exige des preuves de fonctionnement sur les versions actives, sans prétendre qualifier HID/captures. Une nouvelle demande de consentement est obligatoire avant tout essai matériel. Si une opération échoue : arrêt borné, restauration vérifiée ou `RECOVERY_REQUIRED`, et poursuite des travaux indépendants.
