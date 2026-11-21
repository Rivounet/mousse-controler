# Décisions humaines regroupées

## 1. Ressource de signature

Fournir, par un canal secret légitime, le PFX original correspondant au
certificat public déjà approuvé `CN=MousseControler`, et autoriser son import
limité dans `CurrentUser\My` du compte de build. Si cette ressource est perdue,
décider explicitement de créer une nouvelle identité et d'autoriser sa procédure
de confiance ; ce repli est plus risqué.

## 2. Inspections passives hors sandbox

Autoriser une exécution passive limitée :

- requête d'état et historique de la seule tâche `MousseControler-HOGP` depuis
  sa session propriétaire ordinaire ;
- SSH en lecture seule via l'alias exact documenté pour inventorier
  PositionAgent, sa tâche, sa session, sa sauvegarde et `RECOVERY_REQUIRED`.

Aucune élévation, ACL, tâche temporaire ou règle réseau n'est demandée.

## 3. Portes opérationnelles ultérieures

Après résolution des deux points précédents, décider séparément :

1. installation du MSIX signé et mise à jour transactionnelle PositionAgent ;
2. promotion de configuration et activation progressive ;
3. qualification matérielle avec consentement explicite.

Ces trois portes ne sont pas accordées par le présent mandat.
