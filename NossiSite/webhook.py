import subprocess
import time
from threading import Thread

import base64
import json
import logging

from flask import request, abort

import requests
from OpenSSL.crypto import verify, load_publickey, FILETYPE_PEM, X509
from OpenSSL.crypto import Error as SignatureError

from NossiSite.base import webhook, app


@webhook.hook()
def on_push(req):
    def check():
        res = subprocess.run(
            ["nossilint", req["after"]], capture_output=True, encoding="utf-8"
        )
        result = res.stdout
        if result:
            print("update lint result ", result)
        else:
            print("update lint successfull")
        if req["repository"]["name"] == "NossiNet":
            if not result.strip():
                time.sleep(2)
                print("new version checks out. restarting...")
                subprocess.run(["nossirestart"])
            else:
                print("new version didnt pass lint")
                raise Exception("Didnt pass lint!")
            print("we should have never gotten here")

    Thread(target=check).start()
    print("handled github webhook")


@app.route("/travis", methods=["POST"])
def travis():
    logger = logging.getLogger(__name__)

    # https://api.travis-ci.org/config
    # https://api.travis-ci.com/config
    travis_config_url = "https://api.travis-ci.org/config"

    def check_authorized(sig, pkey, payload):
        """
        Convert the PEM encoded public key to a format palatable for pyOpenSSL,
        then verify the signature
        """
        pkey_public_key = load_publickey(FILETYPE_PEM, pkey)
        certificate = X509()
        certificate.set_pubkey(pkey_public_key)
        verify(certificate, sig, payload, str("sha1"))

    def _get_signature():
        """
        Extract the raw bytes of the request signature provided by travis
        """
        print("HEADERS:", request.headers)
        return base64.b64decode(request.headers["Signature"])

    def _get_travis_public_key():
        """
        Returns the PEM encoded public key from the Travis CI /config endpoint
        """
        response = requests.get(travis_config_url, timeout=10.0)
        response.raise_for_status()
        return response.json()["config"]["notifications"]["webhook"]["public_key"]

    signature = _get_signature()
    json_payload = request.get_data()
    print("PAYLOAD:", json_payload)
    return
    try:
        public_key = _get_travis_public_key()

    except requests.Timeout:
        logger.error(
            {"message": "Timed out when attempting to retrieve Travis CI public key"}
        )
        return (
            {"status": "failed"},
            400,
            {"Content-Type": "text/json; charset=utf-8"},
        )
    except requests.RequestException as e:
        logger.error(
            {
                "message": "Failed to retrieve Travis CI public key",
                "error": str(e.args),
            }
        )
        return (
            {"status": "failed"},
            400,
            {"Content-Type": "text/json; charset=utf-8"},
        )
    print("PUBLIC_KEY:", public_key)
    try:
        check_authorized(signature, public_key, json_payload)
    except SignatureError:
        logger.error(f"Unauthorized request by { request.remote_addr}")
        return abort(400)
    json_data = json.loads(json_payload)
    logger.info(f"RECEIVED: { json_data}")
    return {"status": "received"}