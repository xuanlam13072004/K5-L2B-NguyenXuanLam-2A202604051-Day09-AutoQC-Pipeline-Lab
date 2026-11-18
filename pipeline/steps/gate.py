"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.

  còn ≥ 1 lỗi bắt buộc (ERROR)                                   -> "Rework"
  không còn lỗi bắt buộc, tỉ lệ ẢNH còn cảnh báo >= warn_ratio_hold -> "Hold"
  còn lại                                                         -> "Release"
"""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    thr = cfg["gate"]["warn_ratio_hold"]

    # Lỗi bắt buộc: KHÔNG bao giờ bỏ qua, kể cả ở ảnh người đã duyệt
    n_err = sum(i.severity == ERROR for i in issues)

    # Đếm ẢNH (không phải issue) còn cảnh báo: chỉ ảnh có trong dataset, bỏ ảnh đã được người duyệt
    # (issue cấp dataset như "<dataset>", "data.yaml" không nằm trong stems nên tự bị loại)
    warn_imgs = {i.image for i in issues if i.severity == WARN and i.image in stems and i.image not in reviewed}
    n = len(stems)
    ratio = round(len(warn_imgs) / n, 4) if n else 0   # tránh chia cho 0 khi dataset rỗng

    if n_err:
        decision = "Rework"
        reasons = [f"còn {n_err} lỗi bắt buộc chưa sửa"]
    elif ratio >= thr:
        decision = "Hold"
        reasons = [f"{len(warn_imgs)}/{n} ảnh ({ratio:.1%}) còn cảnh báo chưa người duyệt, >= ngưỡng {thr:.0%}"]
    else:
        decision = "Release"
        reasons = [f"0 lỗi bắt buộc; {len(warn_imgs)}/{n} ảnh ({ratio:.1%}) còn cảnh báo, < ngưỡng {thr:.0%}"]

    return dict(decision=decision, n_errors=n_err, n_warn_images=len(warn_imgs),
                n_images=n, warn_ratio=ratio, reasons=reasons)
