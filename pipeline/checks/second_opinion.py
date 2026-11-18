"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l). Chỉ CẢNH BÁO (model cũng có thể sai).

`preds[stem]` = list [id_lớp, conf, cx, cy, w, h] của model. Ngưỡng ở cfg["second_opinion"].
Mỗi dự đoán sinh tối đa 1 issue: POSSIBLE_MISSING / POSSIBLE_LOOSE_BOX / POSSIBLE_WRONG_CLASS;
mỗi dòng nhãn không khớp dự đoán nào -> POSSIBLE_FALSE_POS (có số dòng).
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    s = cfg["second_opinion"]
    if preds is None:
        preds = get_preds(ds, cfg, "checker")                     # dự đoán đã lưu trong data/cache/
    issues = []

    for img in ds.image_files():
        stem = img.stem
        lines = ds.read_label_lines(stem)
        if stem not in preds or lines is None:                     # không có dự đoán / không có file nhãn: bỏ qua
            continue
        size = ds.image_size(stem)
        if not size:
            continue
        W, H = size

        # Nhãn hợp lệ KÈM số dòng gốc (valid_boxes làm mất số dòng nên tự parse)
        labels = []                                                # [(số dòng, (lớp, cx, cy, w, h))]
        for n, text in lines:
            try:
                b = parse_yolo_line(text)
            except ValueError:
                continue                                           # dòng hỏng: label_format đã báo
            if 0 <= b[0] < len(ds.classes):
                labels.append((n, b))

        def add(code, msg, line=None, **extra):
            issues.append(Issue("second_opinion", WARN, code, stem, msg, line, extra))

        # --- Duyệt từng dự đoán đáng tin (conf đủ cao, đủ lớn)
        for cls, conf, *box in preds[stem]:
            if conf < s["conf"] or box[2] * W * box[3] * H < s["min_area_px"]:
                continue
            # cands: nhãn MỌI lớp chồng lên dự đoán với IoU >= iou_missing
            cands = [(iou_xywh(box, b[1:]), b[0]) for _, b in labels]
            cands = [(v, c) for v, c in cands if v >= s["iou_missing"]]
            same = [v for v, c in cands if c == cls]
            other = [v for v, c in cands if c != cls]

            if not cands:                                          # (1) model thấy vật, nhãn không có box
                add("POSSIBLE_MISSING", f"model thấy {ds.classes[int(cls)]} (conf {conf:.2f}) mà nhãn không có",
                    conf=conf, pred_cls=int(cls))
            elif same:                                             # (2) có nhãn đúng lớp
                if max(same) < s["iou_loose"]:
                    add("POSSIBLE_LOOSE_BOX", f"box đúng lớp nhưng lỏng/lệch (IoU {max(same):.2f})",
                        conf=conf, iou=round(max(same), 3))
                # IoU đủ tốt: nhãn đã phủ vật này -> im lặng
            elif max(other) >= s["iou_match"]:                     # (3) chỉ có nhãn khác lớp, trùng khớp tốt
                add("POSSIBLE_WRONG_CLASS", f"model nói {ds.classes[int(cls)]} (conf {conf:.2f}), nhãn khác lớp",
                    conf=conf, iou=round(max(other), 3), pred_cls=int(cls))
            # khác lớp nhưng IoU mơ hồ [iou_missing, iou_match): không cờ

        # --- Box nhãn không khớp dự đoán nào (dùng fp_conf, KHÔNG lọc diện tích)
        loose_preds = [p[2:] for p in preds[stem] if p[1] >= s["fp_conf"]]
        for n, b in labels:
            if all(iou_xywh(b[1:], q) < s["iou_missing"] for q in loose_preds):
                add("POSSIBLE_FALSE_POS", f"box nhãn lớp {ds.classes[b[0]]} không khớp vật nào model thấy", line=n)
    return issues
