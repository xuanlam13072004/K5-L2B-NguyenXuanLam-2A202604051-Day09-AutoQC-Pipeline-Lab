"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).
ERROR: BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, BOX_OUT_OF_IMAGE, DUP_BOX  ·  WARN: BOX_TINY, BOX_HUGE
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    # Mọi ngưỡng đọc từ cfg, không viết cứng
    c = cfg["label_format"]
    tol, min_px, max_frac, dup_iou = c["overflow_tol"], c["min_box_px"], c["max_box_frac"], c["dup_box_iou"]
    n_cls = len(ds.classes)
    issues = []

    for img in ds.image_files():                       # sắp xếp theo tên -> kết quả ổn định giữa các lần chạy
        stem = img.stem
        lines = ds.read_label_lines(stem)              # [(số dòng gốc, nội dung)], đã bỏ dòng trống nhưng GIỮ số dòng
        if lines is None:                              # thiếu file nhãn: check missing_labels đã báo
            continue
        size = ds.image_size(stem)                     # (W, H) px, None nếu ảnh hỏng
        seen = []                                      # các box hợp lệ phía trước: (lớp, (x, y, w, h))

        for ln_no, text in lines:
            def add(sev, code, msg, **extra):
                issues.append(Issue("label_format", sev, code, stem, msg, ln_no, extra))

            # 1) Định dạng: dòng hỏng không được làm script chết -> try/except
            try:
                cls, x, y, w, h = parse_yolo_line(text)
            except ValueError as e:
                add(ERROR, "BAD_FORMAT", f"dòng sai định dạng: {e}")
                continue                               # dòng hỏng thì không kiểm hình học nữa
            # 2) ID lớp
            if not 0 <= cls < n_cls:
                add(ERROR, "BAD_CLASS_ID", f"id lớp {cls} ngoài 0..{n_cls - 1}")
                continue
            # 3) Box rỗng
            if w <= 0 or h <= 0:
                add(ERROR, "BOX_ZERO", f"box rộng/cao <= 0 (w={w}, h={h})")
                continue

            # 4) Tràn ảnh: mức tràn lớn nhất trong 4 mép (trái, phải, trên, dưới)
            over = max(0 - (x - w / 2), (x + w / 2) - 1, 0 - (y - h / 2), (y + h / 2) - 1, 0)
            if over > tol:                             # lớn hơn HẲN tol; chạm đúng 1.0 thì không báo
                add(ERROR, "BOX_OUT_OF_IMAGE", f"box tràn ảnh {over:.4f}", overflow=round(over, 6))

            # 5) Box lặp: cùng lớp với một dòng TRƯỚC và IoU > ngưỡng -> báo ở dòng sau
            box = (x, y, w, h)
            if any(pc == cls and iou_xywh(pb, box) > dup_iou for pc, pb in seen):
                add(ERROR, "DUP_BOX", "box lặp với một dòng trước (cùng lớp)")
            seen.append((cls, box))

            # 6) Cảnh báo kích thước: cạnh NGẮN (px) quá nhỏ, hoặc box gần phủ cả ảnh
            if size and min(w * size[0], h * size[1]) < min_px:
                add(WARN, "BOX_TINY", f"cạnh ngắn {min(w * size[0], h * size[1]):.1f}px < {min_px}px")
            if w * h > max_frac:
                add(WARN, "BOX_HUGE", f"box chiếm {w * h:.0%} ảnh")
    return issues
