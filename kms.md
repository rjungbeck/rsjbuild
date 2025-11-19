# Key Management for Codesigning
## Background
Currently Authenticode codesigning keys have to be stored in HSM (Hardware Security Module) or secure tokens 
(e.g. Yubikey). They mus be NON EXPORTABLE from these hardware.

## Implementation
1) The private key is created in AWS KWS. Assign an alias (alias/github-codesigning-key)
2) The public key has been exported from AWS KWS and converted (on devhost) with aws-kms-sign-csr into CSR:
   1) Create a dummy private key open ssl: openssl genrsa -out dummy.key 4096
   2) Create CSR: openssl req -new -key dummy.key -out dummy.csr
   3) Sign this CSR with aws-kms-sign-csr: aws-kms-sign-csr --key-id (on AWS) --csr dummy.csr --output dummy.pem
   4) Send this CSR to Certificate Authority (CA)
3) We used https://cheapsslsh.com/ for a FastSSL OV codesigning certificate
4) We store the certificate in PEM format (with all intermediate certs) base64 encoded in vars.PUBLIC_CERT_BASE64
5) We connected Github via IAM to Amazon AWS:
   1) Create an Identity Provider for Github in AWS IDAM.
   2) Create a role to map the Github repos to an IAM role (github-user). Use a Trust relastionship to match the sub field to the repo)
   3) Give the role permission to sign code with the key in AWS KMS.

6) Create an ODIC token in Github Actions with aws-actions/configure-aws-credentials@v4 for the role github-user. This also needs to add permissions to sign code with the key in AWS KMS. read/write the token.
7) Adapt rsjbuild:
    1) Use signtool to create the digest file
    2) Use boto3 to sign the digest file with the key in AWS KMS
    3) Use signtool to append the signature to the executable
    4) Use signtool to append a timestamp to the executable
 