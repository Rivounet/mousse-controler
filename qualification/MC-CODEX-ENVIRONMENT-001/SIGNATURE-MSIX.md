# Signature MSIX — transition préparée

## État qualifié

- Sujet : `CN=MousseControler`, identique au `Publisher` du manifeste.
- Clé : RSA 3072 / SHA-256, usage Code Signing, magasin `CurrentUser\My`.
- Stockage : PFX chiffré hors dépôt, mot de passe DPAPI CurrentUser, ACL
  utilisateur courant + SYSTEM seulement.
- Artefact : identité `Rivounet.MousseControler.Hogp`, version 1.0.0.3,
  SHA-256 `54BBC9F547E3A4F12125A55585B9EA0AB4947F4CAF403E663043E90367CC6336`.
- Signature : embarquée, certificat signataire identique à la clé qualifiée.
- Confiance : absente par conception; le message Authenticode indique une
  chaîne terminée par une racine non approuvée.

## Transition Windows

Une mise à jour exige la même identité de paquet, un publisher concordant, une
version supérieure et la confiance dans le nouveau certificat. Les trois
premières conditions sont qualifiées. Sous un mandat distinct, il faudra :

1. sauvegarder l'état et confirmer la version 1.0.0.2 active;
2. installer uniquement le certificat public v2 dans le magasin de confiance
   approprié au périmètre d'installation;
3. revérifier la chaîne, puis installer le MSIX 1.0.0.3;
4. valider alias, configuration et santé avant toute activation.

## Restauration

`Prepare-MsixSigning.ps1 -Action Restore` réimporte le PFX dans
`CurrentUser\My` à partir du secret DPAPI; ce chemin a réussi sans toucher à la
confiance. Pour un échec de mise à jour, conserver le MSIX 1.0.0.2 et son ancien
certificat jusqu'à validation complète. Le retour n'est pas une mise à niveau
inverse : il faut retirer la 1.0.0.3 puis réinstaller la 1.0.0.2 sous autorisation,
en restaurant auparavant les sauvegardes de configuration et de persistance.
