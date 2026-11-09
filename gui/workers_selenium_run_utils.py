import time


def selenium_run(self):
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
