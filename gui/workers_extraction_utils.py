import json


def extract_site_rows(self, driver, wait, site, expected_conditions, by):
    from selenium.common.exceptions import TimeoutException

    try:
        return self._extract_site_rows_impl(driver, wait, site, expected_conditions, by)
    except TimeoutException as exc:
        raise RuntimeError(
            f"Timeout pendant l'extraction de '{site}' (navigation, capteurs ou réponse TOA)."
        ) from exc


def extract_site_rows_impl(self, driver, wait, site, expected_conditions, by):
    self._open_site_from_sidebar(driver, wait, site)
    wait.until(lambda current_driver: "/App/Singlesite" in current_driver.current_url)
    wait.until(lambda current_driver: current_driver.execute_script("return document.readyState") == "complete")
    wait.until(expected_conditions.element_to_be_clickable((by.ID, "analytics-tab"))).click()
    site_rows = []
    for range_start, range_end in [(self.start_date, self.end_date)]:
        wait.until(expected_conditions.element_to_be_clickable((by.ID, "graesDatePickerElem"))).click()
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
        if applied_end < range_start or applied_start > range_end or applied_end < applied_start:
            continue
        if (applied_start, applied_end) != (self.start_date, self.end_date):
            self.dates_adjusted.emit(applied_start, applied_end)

        wait.until(expected_conditions.element_to_be_clickable((
            by.XPATH,
            "//div[contains(@class, 'paramItemHeader') and normalize-space()='Fuel Sensor (01)']",
        ))).click()
        wait.until(expected_conditions.element_to_be_clickable((
            by.XPATH,
            "//div[contains(@class, 'pocketItemHeader') and normalize-space()='FS 4-20mA']",
        ))).click()
        for element_id in (
            "element-MFSX-01-1-4--1",
            "element-MFSX-01-1-6--1",
            "element-MFSX-01-1-12-6",
        ):
            element = wait.until(expected_conditions.presence_of_element_located((by.ID, element_id)))
            if not element.is_selected():
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(by.CSS_SELECTOR, f"label[for='{element_id}']"),
                )
            wait.until(lambda _, checkbox=element: checkbox.is_selected())
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
        wait.until(expected_conditions.element_to_be_clickable((by.ID, "btnShowGraph"))).click()
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
