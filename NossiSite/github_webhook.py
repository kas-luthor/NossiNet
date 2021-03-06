import subprocess
import time
from threading import Thread

from NossiSite.base import webhook


@webhook.hook()
def on_push(request):
    def check():
        res = subprocess.run(["nossilint", request["after"]], capture_output=True, encoding="utf-8")
        result = res.stdout
        if result:
            print("update lint result ", result)
        else:
            print("update lint successfull")
        if request["repository"]["name"] == "NossiNet":
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
