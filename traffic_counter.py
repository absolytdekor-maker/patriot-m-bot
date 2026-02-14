import argparse
import csv
import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


Point = Tuple[int, int]
Line = Tuple[Point, Point]


@dataclass
class DirectionConfig:
    name: str
    line: Line


@dataclass
class Track:
    object_id: int
    centroid: Point
    bbox: Tuple[int, int, int, int]
    missed: int = 0


class CentroidTracker:
    def __init__(self, max_missed: int = 10, max_distance: float = 70.0):
        self.max_missed = max_missed
        self.max_distance = max_distance
        self.next_id = 1
        self.tracks: Dict[int, Track] = {}

    def update(self, detections: List[Tuple[int, int, int, int]]) -> Dict[int, Track]:
        if not detections:
            for track in self.tracks.values():
                track.missed += 1
            self._cleanup()
            return self.tracks

        centroids = [self._bbox_centroid(b) for b in detections]

        if not self.tracks:
            for det, ctr in zip(detections, centroids):
                self._create_track(det, ctr)
            return self.tracks

        track_ids = list(self.tracks.keys())
        track_centroids = [self.tracks[t_id].centroid for t_id in track_ids]

        distance_matrix = np.zeros((len(track_centroids), len(centroids)), dtype=np.float32)
        for i, t_ctr in enumerate(track_centroids):
            for j, d_ctr in enumerate(centroids):
                distance_matrix[i, j] = math.dist(t_ctr, d_ctr)

        used_tracks = set()
        used_dets = set()

        while True:
            if distance_matrix.size == 0:
                break
            i, j = np.unravel_index(np.argmin(distance_matrix), distance_matrix.shape)
            min_distance = distance_matrix[i, j]
            if min_distance > self.max_distance:
                break

            track_id = track_ids[i]
            if track_id in used_tracks or j in used_dets:
                distance_matrix[i, j] = np.inf
                continue

            self.tracks[track_id].centroid = centroids[j]
            self.tracks[track_id].bbox = detections[j]
            self.tracks[track_id].missed = 0
            used_tracks.add(track_id)
            used_dets.add(j)
            distance_matrix[i, :] = np.inf
            distance_matrix[:, j] = np.inf

        for track_id in track_ids:
            if track_id not in used_tracks:
                self.tracks[track_id].missed += 1

        for j, det in enumerate(detections):
            if j not in used_dets:
                self._create_track(det, centroids[j])

        self._cleanup()
        return self.tracks

    def _create_track(self, bbox: Tuple[int, int, int, int], centroid: Point) -> None:
        self.tracks[self.next_id] = Track(
            object_id=self.next_id,
            centroid=centroid,
            bbox=bbox,
            missed=0,
        )
        self.next_id += 1

    def _cleanup(self) -> None:
        remove_ids = [t_id for t_id, tr in self.tracks.items() if tr.missed > self.max_missed]
        for t_id in remove_ids:
            del self.tracks[t_id]

    @staticmethod
    def _bbox_centroid(bbox: Tuple[int, int, int, int]) -> Point:
        x, y, w, h = bbox
        return x + w // 2, y + h // 2


def point_line_side(point: Point, line: Line) -> int:
    (x1, y1), (x2, y2) = line
    px, py = point
    value = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def load_directions(path: str) -> List[DirectionConfig]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    directions = []
    for item in data.get("directions", []):
        name = item["name"]
        p1 = tuple(item["line"][0])
        p2 = tuple(item["line"][1])
        directions.append(DirectionConfig(name=name, line=(p1, p2)))

    if len(directions) != 6:
        raise ValueError("В конфиге должно быть ровно 6 направлений (directions).")
    return directions


def detect_vehicles(frame: np.ndarray, subtractor: cv2.BackgroundSubtractor) -> List[Tuple[int, int, int, int]]:
    mask = subtractor.apply(frame)
    _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 900:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        ratio = w / max(h, 1)
        if w < 25 or h < 25:
            continue
        if ratio > 5.0 or ratio < 0.2:
            continue
        detections.append((x, y, w, h))

    return detections


def save_counts_csv(csv_path: str, counts: Dict[str, int], elapsed_seconds: float) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["направление", "количество"])
        for name, value in counts.items():
            writer.writerow([name, value])
        writer.writerow([])
        writer.writerow(["длительность_сек", f"{elapsed_seconds:.2f}"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Подсчёт транспорта на перекрёстке (6 направлений)")
    parser.add_argument("--source", default="0", help="Источник видео: 0 (камера) или путь к файлу")
    parser.add_argument("--config", default="traffic_directions.example.json", help="JSON с 6 линиями направлений")
    parser.add_argument("--output-csv", default="traffic_counts.csv", help="Куда сохранить итоги")
    args = parser.parse_args()

    directions = load_directions(args.config)
    source = int(args.source) if args.source.isdigit() else args.source

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть источник: {args.source}")

    subtractor = cv2.createBackgroundSubtractorMOG2(history=700, varThreshold=36, detectShadows=True)
    tracker = CentroidTracker(max_missed=10, max_distance=85.0)

    counts = defaultdict(int)
    track_sides: Dict[int, Dict[str, int]] = defaultdict(dict)

    start_time = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        detections = detect_vehicles(frame, subtractor)
        tracks = tracker.update(detections)

        for t_id, track in tracks.items():
            cx, cy = track.centroid
            x, y, w, h = track.bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (40, 180, 40), 2)
            cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)
            cv2.putText(frame, f"ID {t_id}", (x, max(y - 6, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            for direction in directions:
                current_side = point_line_side(track.centroid, direction.line)
                prev_side = track_sides[t_id].get(direction.name)

                if prev_side is not None and prev_side != 0 and current_side != 0 and prev_side != current_side:
                    counts[direction.name] += 1

                track_sides[t_id][direction.name] = current_side

        for direction in directions:
            p1, p2 = direction.line
            cv2.line(frame, p1, p2, (255, 120, 0), 2)

        y0 = 24
        for idx, direction in enumerate(directions):
            label = f"{direction.name}: {counts[direction.name]}"
            cv2.putText(frame, label, (12, y0 + idx * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 255, 255), 2)

        cv2.putText(
            frame,
            "ESC - выход, P - пауза",
            (12, frame.shape[0] - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (220, 220, 220),
            1,
        )

        cv2.imshow("Traffic Counter", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break
        if key in (ord("p"), ord("P")):
            cv2.waitKey(0)

    elapsed = time.time() - start_time
    cap.release()
    cv2.destroyAllWindows()

    save_counts_csv(args.output_csv, dict(counts), elapsed)
    print("Итоговый подсчёт:")
    for direction in directions:
        print(f"- {direction.name}: {counts[direction.name]}")
    print(f"CSV сохранён: {args.output_csv}")


if __name__ == "__main__":
    main()
