import os
from src.dataset import list_csv_files, load_annotations, WINDOW_SIZE
from src.predict import _smooth
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from utils.evaluate_events import ANNOTATIONS, DATA_FOLDER, PERSISTENCE_VALUES

def evaluate(raw_pred, groups_test, annotations, csv_files, min_consecutive):
    detected, missed_list = 0, []
    clean_total, clean_false = 0, 0

    for gi in sorted(set(groups_test.tolist())):
        fname = os.path.basename(csv_files[gi])
        pred_file = _smooth(raw_pred[groups_test == gi], min_consecutive)
        intervals = annotations.get(fname, [])
        if intervals:
            found, missed = _evaluate_intervals(pred_file, intervals, fname)
            detected += found
            missed_list.extend(missed)
        else:
            clean_total += 1
            clean_false += int(pred_file.any())

    return detected, missed_list, clean_total, clean_false


def _evaluate_intervals(pred_file, intervals, fname):
    missed = []
    detected = 0
    for s, e in intervals:
        if pred_file[max(0, s - (WINDOW_SIZE - 1)):e + 1].any():
            detected += 1
        else:
            missed.append((fname, s, e))
    return detected, missed


def _test_indices(X, y, groups):
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    _, test_idx = next(splitter.split(X, y, groups))
    return test_idx


def _print_evaluation(y_test, raw_pred, groups_test):
    print("\n=== Niveau fenêtre (sans persistance) ===")
    print(classification_report(y_test, raw_pred, zero_division=0))
    print("\n=== Comparatif des règles de persistance ===")
    print(f"{'MIN_CONSECUTIVE':>16} | {'evenements detectes':>20} | {'fichiers propres avec fausse alerte':>36}")


def _compare_persistence(raw_pred, groups_test):
    annotations = load_annotations(ANNOTATIONS)
    csv_files = list_csv_files(DATA_FOLDER)
    missed_list = []
    for mc in PERSISTENCE_VALUES:
        detected, missed_list, clean_total, clean_false = evaluate(
            raw_pred, groups_test, annotations, csv_files, mc)
        total = detected + len(missed_list)
        det_rate = detected / total if total else 0
        false_rate = clean_false / clean_total if clean_total else 0
        print(f"{mc:>16} | {detected}/{total} ({det_rate:.3f}){'':>4} | {clean_false}/{clean_total} ({false_rate:.3f})")
    return missed_list

