"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.

`fix(ds, issues, cfg) -> list[dict]` (image, line, action, before, after) = nội dung 03_fixes.csv.
  BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX       -> drop_line
  BOX_OUT_OF_IMAGE                                  -> clip_box (hết diện tích thì drop_line)
  MISSING_LABEL_FILE                                -> needs_label (KHÔNG tạo file nhãn)
  BAD_CLASS_NAME                                    -> rename_classes
  DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE   -> remove_image
Chỉ sửa lỗi ERROR, chỉ sửa trong `ds` (không đụng data/raw), chạy lại lần 2 không làm gì thêm.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}          # + mọi mã bắt đầu bằng DUP_IMAGE_


def fix(ds, issues, cfg):
    fixes = []
    errors = [i for i in issues if i.severity == ERROR]            # cảnh báo WARN là việc của người
    removed = set()

    # Lượt 1: xoá ảnh (và nhãn) trước, để các issue dòng của ảnh đó được bỏ qua êm
    for i in errors:
        if i.code.startswith("DUP_IMAGE_") or i.code in REMOVE_CODES:
            p = ds.image_path(i.image)
            if p is None:                                          # đã xoá rồi (nhiều issue cho cùng ảnh)
                continue
            p.unlink()
            ds.label_path(i.image).unlink(missing_ok=True)
            removed.add(i.image)
            fixes.append(dict(image=i.image, line="", action="remove_image", before=p.name, after="(đã xoá)"))

    # Lượt 2: gom việc theo file nhãn: per_file[stem][số dòng gốc] = "drop" | "clip"
    per_file = defaultdict(dict)
    for i in errors:
        if i.image in removed:
            continue
        if i.code == "MISSING_LABEL_FILE":
            # Máy không bịa nhãn; file rỗng nghĩa là "ảnh nền" nên cũng không tạo -> chuyển người gán
            fixes.append(dict(image=i.image, line="", action="needs_label",
                              before="(không có file)", after="chuyển người gán"))
        elif i.code == "BAD_CLASS_NAME":
            d = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
            before = d.get("names")
            d["names"] = {k: v for k, v in enumerate(cfg["classes"])}
            ds.yaml_path.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
            fixes.append(dict(image="data.yaml", line="", action="rename_classes",
                              before=str(before), after=str(cfg["classes"])))
        elif i.line is not None and (i.code in DROP_CODES or i.code == "BOX_OUT_OF_IMAGE"):
            want = "drop" if i.code in DROP_CODES else "clip"
            cur = per_file[i.image].get(i.line)
            # Một dòng có 2 lỗi (vd. tràn + lặp): xoá thắng, không clip nữa
            per_file[i.image][i.line] = "drop" if "drop" in (cur, want) else "clip"

    # Lượt 3: mỗi file ghi lại MỘT lần, theo số dòng GỐC (kể cả dòng trống) -> không lệch dòng
    for stem, actions in per_file.items():
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        out = []
        for n, text in enumerate(lp.read_text(encoding="utf-8").splitlines(), 1):
            act = actions.get(n)
            if act == "clip":
                new = _clip(text)
                if new is not None:
                    out.append(new)
                    fixes.append(dict(image=stem, line=n, action="clip_box", before=text, after=new))
                    continue
                act = "drop"                                       # box nằm hẳn ngoài ảnh -> xoá
            if act == "drop":
                fixes.append(dict(image=stem, line=n, action="drop_line", before=text, after="(xoá dòng)"))
                continue
            out.append(text)                                       # dòng không lỗi: giữ nguyên
        lp.write_text("".join(l + "\n" for l in out), encoding="utf-8")
    return fixes


def _clip(text):
    """Cắt box về trong [0,1], giữ lớp. Trả None nếu sau khi cắt không còn diện tích."""
    try:
        c, x, y, w, h = parse_yolo_line(text)
    except ValueError:
        return None
    x1, y1 = max(0.0, x - w / 2), max(0.0, y - h / 2)
    x2, y2 = min(1.0, x + w / 2), min(1.0, y + h / 2)
    if x2 <= x1 or y2 <= y1:
        return None
    return f"{c} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"
