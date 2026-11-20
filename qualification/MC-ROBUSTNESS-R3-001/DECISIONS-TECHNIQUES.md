# MC-ROBUSTNESS-R3-001 — décisions techniques

## D-R3-01 — quota sur le pic physique avant admission

Le plafond porte sur tous les octets présents dans le répertoire privé, pas
seulement sur les captures référencées par l'index. Le calcul anticipe aussi la
coexistence nécessaire de l'ancien index et de son fichier temporaire atomique.
Cette approche est volontairement conservatrice : un fichier inconnu réduit la
capacité disponible au lieu d'être ignoré ou supprimé.

## D-R3-02 — sérialiser admission, écriture et commit

Le verrou du broker reste détenu entre le contrôle du quota et la persistance
de l'index. Deux uploads du même processus ne peuvent donc pas consommer
simultanément le même budget. Le coût est une sérialisation des captures, déjà
ponctuelles et bornées par le contrat produit.

## D-R3-03 — réconcilier sans supprimer

Un index absent, invalide ou incomplet ne justifie jamais la suppression d'un
fichier. L'index invalide est préservé et chaque fichier non suivi devient un
enregistrement récupéré `DELETE_FAILED`. Cela privilégie la traçabilité et le
retry contrôlé au nettoyage automatique.

## D-R3-04 — pile de ressources explicite et idempotente

Le runtime enregistre chaque serveur dès que sa construction réussit. La pile
ferme en ordre inverse, continue après chaque exception et agrège les erreurs.
Cette structure couvre uniformément l'initialisation partielle, le démarrage
partiel des threads, le signal d'arrêt et les fermetures répétées.

## D-R3-05 — restauration avant nouvelle installation

Le marqueur transactionnel est l'autorité durable sur une mise à jour
incomplète. Après remplacement, tout échec déclenche au plus deux restaurations
de la sauvegarde vérifiée. Si santé et redémarrage ne sont pas confirmés, le
marqueur reste `RECOVERY_REQUIRED` et une nouvelle installation est refusée :
une seconde mutation ne doit pas masquer la première panne.

## D-R3-06 — injection limitée au harness

Les points de panne sont des paramètres cachés du script réel afin de tester le
vrai chemin transactionnel. Leur usage exige explicitement la variable
`MC_POSITION_AGENT_TRANSACTION_TEST=1`; le harness remplace les cmdlets Windows
et travaille dans un répertoire temporaire. Les tests ne créent ni ne modifient
aucune tâche planifiée.
