# Báo cáo Day 09 — Nguyễn Xuân Lam, 2A202604051

> Mọi số liệu lấy từ `submission/reports/` (lần chạy `python -m pipeline.run` với `phash_dist=12`, `second_opinion.conf=0.6`) và `submission/calibration/`.

## 1. Kết luận trước
**HOLD** (mã thoát 10). Pipeline quét **224** ảnh, nhận **202** ảnh (loại 22 ở cửa vào), xuất **202** ảnh ra `submission/export/clean_v1/` dưới dạng **bản nháp, chưa phát hành**.
Lý do: sau tự sửa và người duyệt **không còn lỗi bắt buộc** (0 ERROR trong `07_error_list_v3`), nhưng **38/202 ảnh (18,8%)** vẫn còn cảnh báo chưa được người xem, vượt ngưỡng `warn_ratio_hold = 10%`. Nguyên nhân gốc: hàng đợi cần duyệt có **125 ảnh** trong khi ngân sách chỉ **80 ảnh**.

## 2. Lỗi và phân việc
Số liệu từ `01_intake.csv` + `02_error_list_v1.csv` (danh sách lỗi TRƯỚC khi sửa). Mẫu số: 224 ảnh quét ở cửa vào; 202 ảnh ở QC vòng 1.

| Mã lỗi | Số dòng / ảnh | Ai sửa | Vì sao |
|---|---:|---|---|
| `DUP_IMAGE_EXACT` | 8 ảnh / 224 | máy (xoá ảnh) | trùng byte md5: chắc chắn 100% |
| `DUP_IMAGE_NEAR` | 4 ảnh / 224 | máy (xoá ảnh) | phash ≤ 12, đã mở xem từng cặp |
| `LEAK_TEST` | 5 ảnh / 224 | máy (xoá ảnh) | trùng ảnh test/gold_val: giữ lại sẽ làm số đo test bị thổi phồng |
| `BAD_SIZE` / `CORRUPT_IMAGE` | 3 / 2 ảnh | máy (xoá ảnh) | ảnh < 250 px hoặc không `load()` được |
| `BAD_FORMAT` · `BAD_CLASS_ID` · `BOX_ZERO` · `DUP_BOX` | 3 · 6 · 4 · 7 dòng | máy (`drop_line`, 20 dòng) | dòng không thể dùng được, không có cách sửa an toàn nào khác |
| `BOX_OUT_OF_IMAGE` | 8 dòng | máy (`clip_box`, 8 box) | cắt về [0,1] giữ nguyên lớp, có log trước → sau |
| `BAD_CLASS_NAME` | 2 lỗi / `data.yaml` | máy (`rename_classes`) | tên lớp chuẩn đã có trong cấu hình |
| `MISSING_LABEL_FILE` | 6 ảnh / 202 | **người** (`needs_label`) | máy không bịa nhãn; file rỗng nghĩa là "ảnh nền", khác "chưa gán" |
| `POSSIBLE_MISSING` | 53 lần / 52 ảnh | **người** | ý kiến model lớn: chỉ nghi ngờ, model cũng sai |
| `POSSIBLE_WRONG_CLASS` | 18 / 18 ảnh | **người** | car↔truck↔bus cần nhìn ảnh mới phân xử được |
| `POSSIBLE_LOOSE_BOX` | 28 / 24 ảnh | **người** | độ chặt box là ngữ nghĩa |
| `POSSIBLE_FALSE_POS` | 29 / 27 ảnh | **người** | box thừa hay vật model không nhận ra? |
| `EMPTY_LABEL`, `BOX_TINY`, `BOX_HUGE`, `CLASS_RARE` | 12 · 6 · 3 · 4 | **người** | cảnh báo theo quy tắc dự án |

Tổng: **36 lỗi bắt buộc, 153 cảnh báo** ở vòng 1 → máy thực hiện **36 thay đổi** (`03_fixes.csv`) → còn **6 lỗi bắt buộc** (đều là `MISSING_LABEL_FILE`) ở vòng 2.

**Hàng đợi (`05_review_queue.csv`, 125 ảnh).** Điểm ưu tiên = tổng trọng số mã lỗi × (1 + conf của model). Đứng đầu là `img_0020` (11,5: vừa bị xoá dòng, vừa nghi thiếu nhãn và nhầm lớp), tiếp theo **6 ảnh `NEEDS_LABEL`** (trọng số 10: chưa có nhãn thì không thể Release). Trong 80 ảnh được duyệt, phần lớn là lỗi ngữ nghĩa nặng: `POSSIBLE_MISSING` 50 ảnh, `POSSIBLE_WRONG_CLASS` 18 ảnh. 45 ảnh nằm ngoài ngân sách chủ yếu là cảnh báo nhẹ (`POSSIBLE_LOOSE_BOX` 16, `POSSIBLE_FALSE_POS` 11, `BOX_TINY` 4). Ngân sách 80 ảnh phủ được **74/103 ảnh** có cảnh báo ngữ nghĩa ở vòng 2; sau duyệt `POSSIBLE_MISSING` giảm 52 → 12 ảnh, `POSSIBLE_WRONG_CLASS` 18 → 3 ảnh.

## 3. Calibration (2 ngưỡng)
Sweep trên `data/calib/` (39 ảnh, có đáp án `MANIFEST.csv`), file `submission/calibration/calibration_report.md`. Ô = precision / recall.

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | **12** | `DUP_IMAGE_NEAR` 1,00 / 0,50 → **1,00 / 0,67**; `DUP_IMAGE_EXACT` giữ 1,00 / 1,00 | Ảnh bị cờ trùng sẽ bị **xoá** → giá của FP cao, ưu tiên precision. 4–14 cho cùng P/R trên calib; chọn 12 vì trên raw bắt thêm cặp `img_0186`~`img_0061` (khoảng cách 10, đã mở xem: cùng cảnh) mà không sinh cặp sai. |
| `second_opinion.conf` | 0,25 | **0,6** | `POSSIBLE_MISSING` 0,50 / 1,00 → **0,57 / 1,00**; `POSSIBLE_WRONG_CLASS` 0,56 / 0,83 → **0,62 / 0,83**; `POSSIBLE_LOOSE_BOX` 0,29 / 0,40 → 0,20 / 0,20 | Đây là **cảnh báo cho người**: ưu tiên recall. 0,6 giữ recall MISSING = 1,00 nhưng bớt báo động giả (hàng đợi 145 → 125 ảnh). **Không chọn 0,8** dù 0,8 cho Release (7,9% cảnh báo): recall MISSING tụt 1,00 → 0,75, tức Release nhờ checker mù đi — "Release giả". Cái giá: `LOOSE_BOX` gần như mất tác dụng (xem §4). |

**Chỗ calibration đánh lừa.** Trên calib, `phash_dist = 16` trông tốt nhất (`DUP_IMAGE_NEAR` recall 0,83, precision vẫn 1,00). Nhưng chạy thử với 16 trên lô raw, số ảnh bị loại vì `LEAK_TEST` nhảy **5 → 11** và `DUP_IMAGE_NEAR` **4 → 7**. Mở xem từng cặp thì các cặp mới là ảnh **không liên quan**: `img_0011` (tennis) bị coi là trùng `img_0008` (trượt tuyết); `img_0013` (bàn laptop) bị coi là ảnh test `test_087` (sân bóng chày); `img_0017` (văn phòng) ~ `test_071` (đua ngựa). Calib chỉ có 9 ảnh trùng và không có ca `LEAK_TEST`, nên không thể hiện việc ngưỡng cao so với **kho 140 ảnh test/val** làm số cặp ngẫu nhiên có khoảng cách nhỏ tăng mạnh. Precision 1,00 trên calib không nói gì về raw.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**(a) Gate chặn thật.** Chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb --work work/run_nb` (không có người duyệt): log ghi `kết luận: REWORK — còn 6 lỗi bắt buộc chưa sửa` và `KHÔNG xuất: còn lỗi bắt buộc (Rework)`, **mã thoát 20**, thư mục `work/exp_nb/` **không được tạo**. 6 lỗi đó chính là 6 ảnh `MISSING_LABEL_FILE`: máy không tự gán nhãn, và gate không cho chúng lọt qua. Ở lần chạy chính, người duyệt đã gán nhãn 6 ảnh này nên lỗi bắt buộc về 0 và kết luận chuyển sang Hold.

**(b) Điểm mù đã biết (có bằng chứng):**
1. **Ảnh trùng bị cắt mạnh.** Cặp `img_0084`~`img_0074` là cùng một ảnh bị cắt (phash 16) nhưng **không bị bắt** với `phash_dist = 12` (không có trong `01_intake.csv`). Nâng ngưỡng lên 16 để bắt cặp này thì xoá nhầm ảnh tốt (§3). Không có ngưỡng phash nào vừa bắt được vừa an toàn.
2. **Box lỏng nhẹ.** Ở `conf = 0,6`, `POSSIBLE_LOOSE_BOX` trên calib chỉ còn recall 0,20 (bắt 1/5 lỗi chèn). Box phình 10–30% vẫn có IoU cao với dự đoán nên không bị cờ; 20 ảnh còn cờ LOOSE_BOX ở `07` cũng là phần không ai xem.
3. **Model lớn cũng sai, nên ý kiến thứ hai không phải sự thật.** Sau khi người duyệt **thay hẳn bằng nhãn người**, vẫn còn ảnh bị cờ: `img_0121`, `img_0183`, `img_0199`… vẫn `POSSIBLE_MISSING` (model thấy "person" conf 0,7–0,8 mà nhãn người không gán: người rất nhỏ/xa, guideline bỏ qua); `img_0078`, `img_0083` vẫn `POSSIBLE_WRONG_CLASS` (model nói car). Trên calib, `POSSIBLE_FALSE_POS` chỉ có precision 0,31. Ngược lại, nhầm lớp mà **model cũng nhầm** (truck/bus giống nhau) thì không có cờ nào.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
**Chưa chạy.** Tôi ưu tiên hoàn thành phần lõi (pipeline, calibration, báo cáo) trong thời lượng lab; phần train trên Colab để làm sau nếu còn thời gian. Vì chưa có số liệu nên **không đưa ra kết luận** "clean tốt hơn raw". Lưu ý cho lần train: bản `clean_v1` hiện là bản **Hold** (38 ảnh còn cảnh báo chưa duyệt), và `raw` chứa 5 ảnh trùng tập test, nên mAP của `raw` có thể bị thổi phồng.

## 6. Quyết định và ghi chú AI
**(a) Quyết định: HOLD.** Dataset sạch lỗi bắt buộc nhưng chưa đủ điều kiện phát hành. Để thành **Release** cần: duyệt thêm tối thiểu **18** trong 38 ảnh còn cảnh báo (để tỉ lệ < 10%, tức ≤ 20/202 ảnh), ưu tiên 12 ảnh `POSSIBLE_MISSING` và 3 ảnh `POSSIBLE_WRONG_CLASS` còn lại; hoặc tăng ngân sách duyệt cho lô sau. **Không** hạ `second_opinion.conf` lên 0,8 chỉ để đạt Release (§3).

**(b) Dùng AI (Claude):**
- *Prompt chính:* đưa repo lab cho AI đọc và yêu cầu viết 4 module theo đúng docstring trong stub + test tương ứng; yêu cầu phân tích bảng sweep để chọn 2 ngưỡng.
- *Cách kiểm:* đọc từng dòng (code có chú thích tiếng Việt), chạy `python -m pytest -q` → **79 passed**; chạy `pipeline.run` rồi đối chiếu `03_fixes.csv` (trước → sau) và mở xem các cặp ảnh bị cờ trùng.
- *Một lần AI sai:* khi dò nhiều cặp ngưỡng, AI viết tên thư mục kết quả là `work/r_$pd_$c` — shell hiểu `$pd_` là một biến khác (rỗng), nên các lần chạy với `phash_dist` khác nhau ghi đè lên cùng thư mục; phải sửa thành `${pd}` và chạy lại để có số liệu đúng.
