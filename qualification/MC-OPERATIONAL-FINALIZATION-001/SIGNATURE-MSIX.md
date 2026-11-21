# Signature MSIX — diagnostic et solution retenue

## Identité vérifiée

| Élément | Valeur |
|---|---|
| Nom package | `Rivounet.MousseControler.Hogp` |
| Éditeur manifeste | `CN=MousseControler` |
| Version installée | `1.0.0.2` |
| Version préparée | `1.0.0.3` |
| Hôte | `powershell.exe` Microsoft-signé |
| Alias | `mousse-hogp-packaged.exe` |

L'ancien MSIX passe `SignTool verify /pa`. Son certificat est valide, RSA
2048, autorisé pour la signature numérique et son certificat public exact est
déjà présent dans les magasins `TrustedPeople` utilisateur et machine.

## Blocage démontré

- aucune copie du certificat avec clé privée dans `CurrentUser\My` ou
  `LocalMachine\My` ;
- aucun PFX/P12 dans les chemins projet et sauvegardes ciblés ;
- le MSIX 1.0.0.3 préparé est donc volontairement non signé et échoue à la
  vérification de signature ;
- aucune clé privée n'a été extraite, recherchée arbitrairement ou publiée.

## Solution retenue

Récupérer le PFX original depuis son détenteur ou coffre légitime, vérifier que
son certificat public correspond exactement au signataire du package 1.0.0.2,
puis l'importer sous autorisation dans `CurrentUser\My` du compte de build.
Le certificat public étant déjà approuvé, cette solution n'exige aucun ajout à
un magasin de confiance.

Construire ensuite avec :

```powershell
pwsh -NoProfile -File scripts/build/Build-HogpPackage.ps1 `
  -CertificateThumbprint <empreinte-vérifiée>
```

Contrôles obligatoires : signature `Valid`, `SignTool verify /pa`, nom,
éditeur, architecture x64, version 1.0.0.3, alias, capacité Bluetooth, hôte
Microsoft-signé et SHA-256 final.

## Repli si le PFX original est perdu

Créer une nouvelle identité de signature avec le même sujet exige une décision
de sécurité, une procédure de confiance approuvée et un essai d'upgrade isolé.
Ce repli ne doit pas être choisi tant que la récupération légitime de la clé
originale n'est pas déclarée impossible. Smart App Control et Defender ne
doivent jamais être désactivés.
