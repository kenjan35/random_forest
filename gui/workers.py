"""
Threads d'arrière-plan (QThread) pour que l'interface reste fluide pendant
qu'un fichier ou un dossier entier est en train d'être analysé.
"""

import csv
import json
import os
import tempfile
import time

from PySide6.QtCore import QThread, Signal

from gui.analysis import analyze_file, find_csv_files, AnalysisError


def _timestamp_sort_key(value):
    """Clé de tri chronologique : nombres (epoch) puis texte ISO."""
    if isinstance(value, (int, float)):
        return (0, float(value), "")
    return (1, 0.0, str(value))


class SingleFileWorker(QThread):
    finished_ok = Signal(dict)
    finished_error = Signal(str)

    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path

    def run(self):
        try:
            result = analyze_file(self.csv_path)
        except AnalysisError as exc:
            self.finished_error.emit(str(exc))
        except Exception as exc:  # filet de sécurité pour toute erreur imprévue
            self.finished_error.emit(f"Erreur inattendue : {exc}")
        else:
            self.finished_ok.emit(result)


class BatchScanWorker(QThread):
    progress = Signal(int, int, str)     # (fait, total, nom du fichier en cours)
    file_done = Signal(dict)              # résultat pour un fichier (ou erreur encapsulée)
    finished_all = Signal()

    def __init__(self, folder, parent=None):
        super().__init__(parent)
        self.folder = folder
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        csv_files = find_csv_files(self.folder)
        total = len(csv_files)
        for i, csv_path in enumerate(csv_files, start=1):
            if self._stop_requested:
                break
            filename = os.path.basename(csv_path)
            try:
                result = analyze_file(csv_path)
                result["error"] = None
            except AnalysisError as exc:
                result = {"csv_path": csv_path, "filename": filename, "error": str(exc)}
            except Exception as exc:
                result = {"csv_path": csv_path, "filename": filename, "error": f"Erreur inattendue : {exc}"}
            self.file_done.emit(result)
            # progression émise APRÈS le traitement : 100 % = vraiment terminé
            self.progress.emit(i, total, csv_path)
        self.finished_all.emit()


class SeleniumExtractionWorker(QThread):
    finished_ok = Signal(list)
    result_ready = Signal(dict)
    finished_error = Signal(str)
    dates_adjusted = Signal(str, str)

    def __init__(self, url, user_id, password, start_date, end_date, sites, parent=None):
        super().__init__(parent)
        self.url, self.user_id, self.password = url, user_id, password
        self.start_date, self.end_date = start_date, end_date
        self.sites = sites

    def run(self):
        driver = None
        step = "démarrage de Chrome"
        try:
            try:
                from selenium import webdriver
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Le module Selenium est absent de l'environnement de l'application. "
                    "Lancez installer.bat ou venv\\Scripts\\python.exe -m pip install selenium."
                ) from exc
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            options = webdriver.ChromeOptions()
            options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
            driver = webdriver.Chrome(options=options)
            wait = WebDriverWait(driver, 45)
            step = "ouverture de la page de connexion"
            driver.get(self.url)
            step = "attente du champ identifiant"
            wait.until(EC.presence_of_element_located((By.ID, "UserId"))).send_keys(self.user_id)
            step = "attente du champ mot de passe"
            wait.until(EC.presence_of_element_located((By.ID, "Password"))).send_keys(self.password)
            step = "clic sur le bouton de connexion"
            wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
            # Le side menu et sa liste de sites sont construits après la
            # redirection. Le délai est volontaire pour laisser TOA terminer
            # ses chargements asynchrones.
            time.sleep(7)
            multisite_url = driver.current_url
            results = []
            for site_index, site in enumerate(self.sites):
                site_error = None
                for attempt in range(2):
                    try:
                        if site_index or attempt:
                            driver.get(multisite_url)
                            wait.until(EC.presence_of_element_located((By.ID, "singlesiteviewlist")))
                            time.sleep(2)
                        site_rows = self._extract_site_rows(driver, wait, site, EC, By)
                        site_results = self._analyze_extracted_rows(site_rows)
                        results.extend(site_results)
                        for result in site_results:
                            self.result_ready.emit(result)
                        site_error = None
                        break
                    except Exception as exc:
                        site_error = exc
                if site_error is not None:
                    result = {
                        "site": site,
                        "filename": site,
                        "error": (
                            f"Extraction interrompue pour ce site après 2 tentatives : "
                            f"{type(site_error).__name__}: {site_error}"
                        ),
                    }
                    results.append(result)
                    self.result_ready.emit(result)
            self.finished_ok.emit(results)
        except TimeoutException as exc:
            location = ""
            if driver is not None:
                location = f"\nURL actuelle : {driver.current_url}\nTitre : {driver.title}"
            self.finished_error.emit(
                f"Délai dépassé pendant l'étape : {step}.\n"
                "Le portail TOA n'a pas affiché l'élément attendu dans les 45 secondes."
                f"{location}\n\nDétail technique : {exc}"
            )
        except Exception as exc:
            self.finished_error.emit(f"Erreur pendant l'étape '{step}' : {type(exc).__name__}: {exc}")
        finally:
            if driver is not None:
                driver.quit()

    def _extract_site_rows(self, driver, wait, site, EC, By):
        from selenium.common.exceptions import TimeoutException

        try:
            return self._extract_site_rows_impl(driver, wait, site, EC, By)
        except TimeoutException as exc:
            raise RuntimeError(f"Timeout pendant l'extraction de '{site}' (navigation, capteurs ou réponse TOA).") from exc

    def _extract_site_rows_impl(self, driver, wait, site, EC, By):
        self._open_site_from_sidebar(driver, wait, site)
        wait.until(lambda current_driver: "/App/Singlesite" in current_driver.current_url)
        wait.until(lambda current_driver: current_driver.execute_script("return document.readyState") == "complete")
        wait.until(EC.element_to_be_clickable((By.ID, "analytics-tab"))).click()
        site_rows = []
        # TOA borne déjà la plage à ses dernières données disponibles. Une
        # seconde requête artificielle (par exemple 30/08 -> 31/08 après une
        # première plage 01/08 -> 29/08) provoque parfois un timeout. Une
        # seule requête évite ce cas et conserve toutes les données disponibles.
        for range_start, range_end in [(self.start_date, self.end_date)]:
            wait.until(EC.element_to_be_clickable((By.ID, "graesDatePickerElem"))).click()
            result = driver.execute_script("""
                const input = document.getElementById('graesDatePickerElem');
                if (!input) return 'DATE_INPUT_NOT_FOUND';
                if (!window.jQuery) return 'JQUERY_NOT_FOUND';
                const picker = window.jQuery(input).data('daterangepicker');
                if (!picker) return 'DATE_PICKER_NOT_FOUND';
                if (!window.moment) return 'MOMENT_NOT_FOUND';
                const start = window.moment(arguments[0], 'YYYY-MM-DD');
                const end = window.moment(arguments[1], 'YYYY-MM-DD');
                if (!start.isValid() || !end.isValid()) return 'INVALID_DATE';
                picker.setStartDate(start);
                picker.setEndDate(end);
                picker.updateView();
                picker.updateCalendars();
                picker.updateElement();
                picker.clickApply();
                return {
                    start: picker.startDate.format('YYYY-MM-DD'),
                    end: picker.endDate.format('YYYY-MM-DD'),
                    input: input.value
                };
            """, range_start, range_end)
            if not isinstance(result, dict):
                raise RuntimeError(
                    f"TOA n'a pas pu appliquer la période {range_start} -> {range_end}. "
                    f"Valeur retournée : {result}"
                )
            applied_start = result.get("start")
            applied_end = result.get("end")
            if not applied_start or not applied_end:
                raise RuntimeError(
                    f"TOA n'a pas retourné de période valide pour {range_start} -> {range_end}."
                )
            # Quand la tranche demandée est après le dernier relevé, TOA
            # peut retourner la dernière date disponible (ex. 29/08) au lieu
            # de signaler une tranche vide. Ne lancez pas View Graph dans ce
            # cas : cela provoque un timeout alors qu'il n'y a simplement
            # aucune donnée à extraire.
            if applied_end < range_start or applied_start > range_end or applied_end < applied_start:
                continue
            if (applied_start, applied_end) != (self.start_date, self.end_date):
                self.dates_adjusted.emit(applied_start, applied_end)

            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'paramItemHeader') and normalize-space()='Fuel Sensor (01)']"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'pocketItemHeader') and normalize-space()='FS 4-20mA']"))).click()
            for element_id in (
                "element-MFSX-01-1-4--1",
                "element-MFSX-01-1-6--1",
                "element-MFSX-01-1-12-6",
            ):
                element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
                if not element.is_selected():
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.CSS_SELECTOR, f"label[for='{element_id}']"),
                    )
                wait.until(lambda current_driver, checkbox=element: checkbox.is_selected())
            selected = driver.execute_script("""
                return {
                    fuel: document.getElementById('element-MFSX-01-1-4--1')?.checked === true,
                    tank: document.getElementById('element-MFSX-01-1-6--1')?.checked === true,
                    generator: document.getElementById('element-MFSX-01-1-12-6')?.checked === true
                };
            """)
            if not selected.get("fuel") or not selected.get("tank") or not selected.get("generator"):
                raise RuntimeError(
                    f"Les cases Fuel Volume / Total Tank Volume / Generator Running ne sont pas cochées : {selected}"
                )
            self._install_response_capture(driver)
            driver.execute_script("window.__toaCapturedResponses = [];")
            driver.get_log("performance")
            wait.until(EC.element_to_be_clickable((By.ID, "btnShowGraph"))).click()
            response_body = self._wait_for_captured_response(driver)
            try:
                data = json.loads(response_body)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"GetGrAesData a renvoyé une réponse non JSON pour '{site}' : {response_body[:300]!r}"
                ) from exc
            if data is None:
                raise RuntimeError(f"GetGrAesData a renvoyé null pour '{site}' sur {range_start} -> {range_end}.")
            if isinstance(data, dict):
                data = data.get("data") or data.get("parameters")
            if not isinstance(data, list):
                raise RuntimeError(f"Format inattendu de GetGrAesData pour '{site}' : {type(data).__name__}")
            for parameter in data:
                if not isinstance(parameter, dict):
                    continue
                for value in parameter.get("values") or []:
                    if isinstance(value, dict):
                        site_rows.append({
                            "site": site, "device": parameter.get("device"),
                            "deviceId": parameter.get("deviceId"), "pocket": parameter.get("pocket"),
                            "field": parameter.get("field"), "bitIndex": parameter.get("bitIndex"),
                            "timestamp": value.get("dt"), "value": value.get("val"),
                        })
        return site_rows

    @staticmethod
    def _install_response_capture(driver):
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

    @staticmethod
    def _wait_for_captured_response(driver):
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
            # Certaines versions de TOA utilisent une couche réseau qui ne
            # laisse pas le hook fetch/XHR lire le corps. Le journal CDP reste
            # disponible comme second canal de récupération.
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

    @staticmethod
    def _analyze_extracted_rows(rows):
        """Convertit les paramètres TOA en CSV compatible avec le pipeline."""
        from gui.analysis import FUEL_COLUMN, STATUS_COLUMN, TIMESTAMP_COLUMN, TANK_VOLUME_COLUMN

        results = []
        for site in dict.fromkeys(row["site"] for row in rows):
            site_rows = [row for row in rows if row["site"] == site]
            by_timestamp = {}
            for row in site_rows:
                timestamp = row.get("timestamp")
                field = str(row.get("field") or "").strip()
                bit_index = str(row.get("bitIndex") or "").strip()
                field_lower = " ".join(str(row.get(key) or "") for key in ("field", "pocket", "device")).casefold()
                if timestamp is None:
                    continue
                target = by_timestamp.setdefault(timestamp, {TIMESTAMP_COLUMN: timestamp})
                is_fuel_volume = (
                    (field == "4" and bit_index in ("", "-1", "-1.0"))
                    or ("fuel" in field_lower and ("volume" in field_lower or "ltr" in field_lower))
                )
                is_generator_running = (
                    (field == "12" and bit_index in ("6", "6.0"))
                    or ("generator" in field_lower and "running" in field_lower)
                )
                is_tank_volume = (
                    (field == "6" and bit_index in ("", "-1", "-1.0"))
                    or ("total tank" in field_lower and ("volume" in field_lower or "ltr" in field_lower))
                )
                if is_fuel_volume:
                    target[FUEL_COLUMN] = row.get("value")
                elif is_generator_running:
                    target[STATUS_COLUMN] = row.get("value")
                elif is_tank_volume:
                    target[TANK_VOLUME_COLUMN] = row.get("value")

            # TOA ne garantit pas l'ordre des valeurs : le pipeline exige un ordre chronologique
            csv_rows = sorted(
                (row for row in by_timestamp.values() if FUEL_COLUMN in row and STATUS_COLUMN in row),
                key=lambda row: _timestamp_sort_key(row[TIMESTAMP_COLUMN]),
            )
            if not csv_rows:
                results.append({
                    "site": site,
                    "error": "Les données TOA ne contiennent pas les champs Fuel Volume et Generator Running.",
                })
                continue

            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as file:
                    fieldnames = [TIMESTAMP_COLUMN, FUEL_COLUMN, STATUS_COLUMN]
                    if any(TANK_VOLUME_COLUMN in row for row in csv_rows):
                        fieldnames.append(TANK_VOLUME_COLUMN)
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_rows)
                    temp_path = file.name
                result = analyze_file(temp_path)
                result["site"] = site
                result["filename"] = site
                results.append(result)
            except AnalysisError as exc:
                results.append({"site": site, "filename": site, "error": str(exc)})
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
        return results

    @staticmethod
    def _open_site_from_sidebar(driver, wait, site):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC

        side_menu = wait.until(EC.visibility_of_element_located((By.ID, "singlesiteviewlist")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", side_menu)
        driver.execute_script("arguments[0].click();", side_menu)

        search = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "#singlesiteNavListSearchContainer input[type='search']")
        ))
        search.clear()
        search.send_keys(site)

        site_xpath = (
            "//li[contains(concat(' ', normalize-space(@class), ' '), ' nav__site ')]"
            f"[.//*[contains(concat(' ', normalize-space(@class), ' '), ' title-item ') "
            f"and starts-with(normalize-space(), {SeleniumExtractionWorker._xpath_literal(site)})]]"
        )
        site_item = wait.until(EC.element_to_be_clickable((By.XPATH, site_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", site_item)
        driver.execute_script("arguments[0].click();", site_item)
        wait.until(lambda current_driver: "/App/Singlesite" in current_driver.current_url)

    @staticmethod
    def _xpath_literal(value):
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"
