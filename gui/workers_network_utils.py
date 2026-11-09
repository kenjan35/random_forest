import json
import time


def install_response_capture(driver):
    driver.execute_script("""
        if (window.__toaResponseCaptureInstalled) return;
        window.__toaResponseCaptureInstalled = true;
        window.__toaCapturedResponses = [];
        const isTarget = url => String(url || '').includes('GetGrAesData');

        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const request = originalFetch.apply(this, args);
            request.then(response => {
                if (!isTarget(response.url)) return;
                response.clone().text().then(body => {
                    window.__toaCapturedResponses.push({url: response.url, status: response.status, body});
                });
            }).catch(() => {});
            return request;
        };

        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this.__toaUrl = url;
            return originalOpen.call(this, method, url, ...rest);
        };
        XMLHttpRequest.prototype.send = function(...args) {
            this.addEventListener('load', function() {
                if (isTarget(this.__toaUrl || this.responseURL)) {
                    window.__toaCapturedResponses.push({
                        url: this.responseURL || this.__toaUrl,
                        status: this.status,
                        body: this.responseText
                    });
                }
            });
            return originalSend.apply(this, args);
        };
    """)


def wait_for_captured_response(driver):
    deadline = time.time() + 60
    while time.time() < deadline:
        responses = driver.execute_script("return window.__toaCapturedResponses || [];")
        for response in responses:
            if response.get("status") == 200 and response.get("body"):
                return response["body"]
            if response.get("status", 0) >= 400:
                raise RuntimeError(
                    f"GetGrAesData a répondu HTTP {response['status']} : "
                    f"{str(response.get('body', ''))[:300]}"
                )
        for entry in driver.get_log("performance"):
            try:
                message = json.loads(entry["message"])["message"]
            except (KeyError, TypeError, ValueError):
                continue
            if message.get("method") != "Network.responseReceived":
                continue
            params = message.get("params", {})
            response = params.get("response", {})
            if "GetGrAesData" not in response.get("url", ""):
                continue
            if response.get("status", 0) >= 400:
                raise RuntimeError(f"GetGrAesData a répondu HTTP {response['status']}.")
            try:
                body = driver.execute_cdp_cmd(
                    "Network.getResponseBody",
                    {"requestId": params["requestId"]},
                ).get("body")
                if body:
                    return body
            except Exception:
                continue
        time.sleep(0.2)
    raise RuntimeError(
        "GetGrAesData n'a pas été reçu par fetch/XHR dans les 60 secondes. "
        "Le bouton View Graph n'a probablement pas déclenché la requête."
    )
