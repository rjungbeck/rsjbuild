# Google Key Management
In an first step we load the existing codesigning key into the Goggle KMS and use it for signatures.

In the second step we create a codesigning key directly in Google KMS, and obtain a cert for it and use this key for signatures 

## Create Project
## Create Keyring
````
gcloud kms keyrings create codesigning --location global
````
## Create Key
````
gcloud kms keys create cs2022-3 --keyring codesigning --location global --purpose asymmetric-signing --default-algorithm rsa-sign-pkcs1-sha256 --protection-level hsm
````

## Create Key Import Job
```` 
gcloud kms import-jobs create cs2022-3 --location global --keyring codesigning --protection-level hsm --import-method rsa-oaep-4096-sha256-aes-256
````

## Decrypt Private Key

### Enable legacy encryption methods
/etc/ssl/openssl.cnf:
````
[provider_set]
default = default_sect
legacy = legacy_sect

[default_sect]
activate = 1

[legacy_sect]
activate = 1
````
### Decrypt Private Key
````
openssl pkcs12 -in cs2022.p12 -noenc
````
Select private key and store in cs2022priv.pem

````
openssl pkcs8 -topk8 -nocrypt -inform PEM -outform DER -in cs2022priv.pem -out cs20200priv.der 
````

## Install in KMS

````
gcloud kms keys versions import --target-key-file cs2022priv.der --import-job cs2022-3 --algorithm rsa-sign-pkcs1-3072-sha256 --location global --keyring codesigning --key cs2022-3
````

Private key must be in PKCS8 DER format.

## Sign using jsign

````
wget https://github.com/ebourg/jsign/releases/download/7.1/jsign-7.1.jar

for /f "usebackq tokens=* delims=" %%i in (`gcloud auth print-access-token`) do (
    set "GCP_ACCESS_TOKEN=%%i"
)

java -jar jsign-7.1.jar --storetypoe GOOGLECLOUD --keystore projects/key-mangment-464714/locations/global/keyRings/codesigning --storepass %GCP_ACCESS_TOKEN% <accessToken> --alias cs2022-3 --certfile cs2022cert.pem -t http://timestamp.digicert.com application.exe
````

## Github Actions

```` 
steps:
        [...]

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          java-version: 17
          distribution: 'temurin'

      - name: Download Jsign
        run: wget https://github.com/ebourg/jsign/releases/download/7.1/jsign-7.1.jar

      - name: Sign
        run: >
          java -jar jsign-7.1.jar --storetype TRUSTEDSIGNING
                                  --keystore weu.codesigning.azure.net
                                  --storepass ${{ secrets.AZURE_ACCESS_TOKEN }}
                                  --alias <account>/<profile>
                                  ${{ github.workspace }}/dist/application.exe
````

# Create Google Cloud Identity Pool
````
gcloud iam workload-identity-pools create githubaction --location global --displayName "Github Action" --description "Request from Github Actions" --project key-managment-464714
````
## Create a OIDC Connection
```` 
gcloud iam workload-identity-pools providers create-oidc github-repo --project key-managment-464714 --location global --workload-identity-pool githubaction --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" --attribute-condition="assertion.repository_owner == 'rjungbeck'" --issuer-uri https://token.actions.githubusercontent.com
````

## Describe Identity Provider
````
gcloud iam workload-identity-pools providers describe github-repo --project key-managment-464714 --location global --workload-identity-pool githubaction --format "value(name)"
````