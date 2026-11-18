"""Test cho check thưởng aspect_ratio (học viên viết thêm; không sửa file test ĐÃ VIẾT SẴN)."""
from pipeline.checks import aspect_ratio


def run(make_ds, cfg, lines, size=(640, 480)):
    ds = make_ds(images={"a": 1}, labels={"a": lines}, size=size)
    return [(i.code, i.line, i.severity) for i in aspect_ratio.run(ds, cfg)]


def test_normal_boxes_are_silent(make_ds, cfg):
    # person đứng (0.1*640 / 0.5*480 = 0.27) và car nằm ngang (0.4*640/0.2*480 = 2.67): bình thường
    assert run(make_ds, cfg, ["1 0.5 0.5 0.1 0.5", "0 0.5 0.5 0.4 0.2"]) == []


def test_too_wide_and_too_thin_are_warned_with_line(make_ds, cfg):
    # dòng 2: 0.9*640 / (0.05*480) = 24 (quá dẹt); dòng 3: 0.02*640 / (0.9*480) ≈ 0.03 (quá mảnh)
    got = run(make_ds, cfg, ["1 0.5 0.5 0.1 0.5", "0 0.5 0.5 0.9 0.05", "1 0.5 0.5 0.02 0.9"])
    assert got == [("BOX_EXTREME_ASPECT", 2, "warn"), ("BOX_EXTREME_ASPECT", 3, "warn")]


def test_ratio_is_measured_in_pixels_not_normalised(make_ds, cfg):
    # chuẩn hoá thì w/h = 0.5/0.05 = 10 (> 8), nhưng ảnh 240x640: 0.5*240 / (0.05*640) = 3.75 -> không cờ
    assert run(make_ds, cfg, ["0 0.5 0.5 0.5 0.05"], size=(240, 640)) == []


def test_threshold_from_config_and_default(make_ds, cfg):
    line = ["0 0.5 0.5 0.6 0.1"]                       # 0.6*640 / (0.1*480) = 8.0: đúng ngưỡng mặc định, chưa cờ
    assert run(make_ds, cfg, line) == []
    cfg["aspect_ratio"] = {"max_ratio": 5}
    assert run(make_ds, cfg, line) == [("BOX_EXTREME_ASPECT", 1, "warn")]


def test_broken_lines_do_not_crash_and_keep_line_numbers(make_ds, cfg):
    got = run(make_ds, cfg, ["garbage", "", "93 0.5 0.5 0.9 0.01", "1 0.5 0.5 0 0.5", "0 0.5 0.5 0.9 0.05"])
    assert got == [("BOX_EXTREME_ASPECT", 5, "warn")]


def test_image_without_label_file_is_skipped(make_ds, cfg):
    ds = make_ds(images={"a": 1, "b": 2}, labels={"a": ["1 0.5 0.5 0.1 0.5"]})
    assert aspect_ratio.run(ds, cfg) == []
