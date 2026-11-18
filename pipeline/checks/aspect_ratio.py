"""CHECK THƯỞNG — Box có tỉ lệ khung hình cực đoan (quá dẹt / quá mảnh).   (học viên viết thêm)

Test:  pytest tests/test_aspect_ratio.py -q

Tỉ lệ tính theo PIXEL (không theo toạ độ chuẩn hoá, vì ảnh thường không vuông):
    r = (w * W) / (h * H)      lệch = max(r, 1/r)
Nếu lệch > `max_ratio` -> WARN `BOX_EXTREME_ASPECT` (extra={"aspect": r}).

Vì sao chỉ CẢNH BÁO: vật bị che hoặc bị cắt ở mép ảnh có thể rất dẹt mà vẫn đúng
(nhãn người cũng có box car lệch > 10 do bị che). Box quá dẹt thường là box lỏng/lệch,
box vẽ nhầm hoặc nhãn bị hỏng toạ độ -> chuyển người xem.

Ngưỡng: đọc `cfg["aspect_ratio"]["max_ratio"]` nếu có; nếu không có thì dùng DEFAULTS.
(Không thêm khoá vào configs/pipeline.yaml vì file đó bị khoá theo quy tắc lab.)
Mặc định 8: chọn trên nhãn người sạch (xem submission/REPORT.md, mục Thưởng).

Check này KHÔNG nằm trong QC_CHECKS (pipeline/checks/__init__.py là file ĐÃ VIẾT SẴN, bị khoá),
chạy độc lập:  python -m pipeline.checks.aspect_ratio work/run/ds
"""
from ..common import WARN, Issue, parse_yolo_line

DEFAULTS = {"max_ratio": 8.0}


def run(ds, cfg):
    p = {**DEFAULTS, **(cfg.get("aspect_ratio") or {})}
    max_ratio = float(p["max_ratio"])
    issues = []
    for img in ds.image_files():
        stem = img.stem
        lines = ds.read_label_lines(stem)
        size = ds.image_size(stem)
        if lines is None or not size:                      # thiếu nhãn / ảnh hỏng: check khác đã báo
            continue
        W, H = size
        for n, text in lines:
            try:
                c, x, y, w, h = parse_yolo_line(text)
            except ValueError:
                continue                                   # dòng hỏng: label_format đã báo
            if not 0 <= c < len(ds.classes) or w <= 0 or h <= 0:
                continue                                   # BAD_CLASS_ID / BOX_ZERO: label_format đã báo
            r = (w * W) / (h * H)
            skew = max(r, 1 / r)
            if skew > max_ratio:
                kind = "quá dẹt (ngang)" if r > 1 else "quá mảnh (dọc)"
                issues.append(Issue("aspect_ratio", WARN, "BOX_EXTREME_ASPECT", stem,
                                    f"box {ds.classes[c]} {kind}: rộng/cao = {r:.2f} (> {max_ratio:g} lần)",
                                    n, {"aspect": round(r, 3)}))
    return issues


if __name__ == "__main__":                                 # chạy độc lập trên một dataset YOLO
    import sys
    from collections import Counter

    from ..common import Dataset, load_config, write_issues_csv
    cfg = load_config()
    root = sys.argv[1] if len(sys.argv) > 1 else "work/run/ds"
    out = sys.argv[2] if len(sys.argv) > 2 else "work/aspect_ratio.csv"
    ds = Dataset(root, cfg["classes"])
    iss = run(ds, cfg)
    write_issues_csv(iss, out)
    print(f"quét {len(ds.image_files())} ảnh trong {root}: {len(iss)} box lệch tỉ lệ ở "
          f"{len({i.image for i in iss})} ảnh -> {out}")
    for i in iss:
        print(f"  {i.image} dòng {i.line}: {i.message}")
    print(Counter(i.message.split()[1] for i in iss))
