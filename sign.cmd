for /f "usebackq tokens=* delims=" %%i in (`gcloud auth print-access-token`) do (
    set "GCP_ACCESS_TOKEN=%%i"
)

java -jar jsign-7.1.jar  --storetype GOOGLECLOUD --keystore projects/key-managment-464714/locations/global/keyRings/codesigning --storepass %GCP_ACCESS_TOKEN% --alias cs2022-3 --certfile cs2022cert.pem -t http://timestamp.digicert.com notepad.exe