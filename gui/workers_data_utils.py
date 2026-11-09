import csv
import os
import tempfile

from gui.analysis import AnalysisError, analyze_file
from gui.workers_utils import timestamp_sort_key


def analyze_extracted_rows(rows):
    from gui.analysis import FUEL_COLUMN, STATUS_COLUMN, TIMESTAMP_COLUMN, TANK_VOLUME_COLUMN

    results = []
    for site in dict.fromkeys(row["site"] for row in rows):
        site_rows = [row for row in rows if row["site"] == site]
        by_timestamp = {}
        for row in site_rows:
            timestamp = row.get("timestamp")
            field = str(row.get("field") or "").strip()
            bit_index = str(row.get("bitIndex") or "").strip()
            field_lower = " ".join(
                str(row.get(key) or "") for key in ("field", "pocket", "device")
            ).casefold()
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

        csv_rows = sorted(
            (row for row in by_timestamp.values() if FUEL_COLUMN in row and STATUS_COLUMN in row),
            key=lambda row: timestamp_sort_key(row[TIMESTAMP_COLUMN]),
        )
        if not csv_rows:
            results.append({
                "site": site,
                "error": "Les données TOA ne contiennent pas les champs Fuel Volume et Generator Running.",
            })
            continue

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
            ) as file:
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


def open_site_from_sidebar(driver, wait, site):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from gui.workers_utils import xpath_literal

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
        f"and starts-with(normalize-space(), {xpath_literal(site)})]]"
    )
    site_item = wait.until(EC.element_to_be_clickable((By.XPATH, site_xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", site_item)
    driver.execute_script("arguments[0].click();", site_item)
    wait.until(lambda current_driver: "/App/Singlesite" in current_driver.current_url)
