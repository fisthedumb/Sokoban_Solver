# Project Sokoban:

## GUI xem và đánh giá lời giải

Chạy `python gui.py` (dùng Tkinter có sẵn trong bản cài Python thông thường).
Chọn map, nhập giới hạn thời gian rồi nhấn **Giải** để chạy `solution.solve()`.
Kết quả hiển thị thời gian tìm kiếm, số bước và số lần đẩy; đường đi được kiểm tra
bằng `validation.py` trước khi cho phát lại.

Dùng **Phát / Tạm dừng**, **Về đầu**, **◀ Bước**, **Bước ▶** hoặc phím mũi tên
trái/phải để xem đường đi. Chọn tốc độ theo mili giây mỗi bước.
Bật **Tự điều khiển từ bước hiện tại**, chọn số robot rồi dùng phím mũi tên
để tự chơi từ trạng thái đang xem (nhấp vào bàn chơi nếu bàn phím đang ở ô nhập).
Nút **◀ Bước** hoàn tác; đi hướng khác sau khi hoàn tác sẽ thay nhánh tự chơi.
Nhấn **Quay lại lời giải** hoặc bỏ chọn chế độ tự điều khiển để khôi phục
đường đi gốc và vị trí replay trước khi tự chơi.
**Dừng giải** hủy tìm kiếm hiện tại; chuyển map cũng tự dừng tìm kiếm.
Mỗi lần nhấn **Giải** sẽ nạp lại `solution.py`, nên có thể sửa solver rồi thử lại
mà không cần đóng GUI. File GUI chỉ phục vụ thử nghiệm, bài nộp vẫn là `solution.py`.

Thiết kế chương trình giải Sokoban. Sinh viên tự lựa chọn thuật toán, heuristic,
cấu trúc dữ liệu và chiến lược.

## 1. Framework và bài nộp

Python 3.10+, chỉ dùng thư viện chuẩn Python và framework được cung cấp.
Hoàn thiện `solution.py`, được thêm hàm, lớp và import trong file này.
Chỉ nộp file `solution.py` sau khi hoàn thiện.

| File | Vai trò |
| --- | --- |
| `solution.py` | Hàm `solve` do sinh viên triển khai |
| `state.py`, `sokoban.py` | Trạng thái, luật chơi, hiển thị và 20 map thực hành |
| `validation.py` | Kiểm tra đường đi hợp lệ |
| `public_tests.py`, `autograder.py` | Kiểm tra giao diện cơ bản, không phải điểm chính thức |
| `test_framework.py` | Kiểm tra framework, chạy được trước khi viết solver |
| `REPORT_TEMPLATE.md` | Gợi ý mô tả thiết kế, không có điểm riêng |

Không sửa framework để thay đổi luật chơi. Không viết cứng lời giải theo test,
đọc dữ liệu bộ chấm, truy cập mạng hoặc tạo tiến trình/luồng nền.
Mỗi test chạy trong một tiến trình mới; không lưu dữ liệu giữa các test.

## 2. Luật chơi

- Bàn chơi gồm robot, thùng, ô đích (storage) và tường.
- Mỗi hành động chọn một robot đi một ô lên, phải, xuống hoặc trái.
  Các robot di chuyển lần lượt, không đi xuyên tường hay robot khác.
- Nếu ô kế tiếp có thùng, robot chỉ đẩy được khi ô ngay sau thùng trống
  và nằm trong bàn chơi. Không kéo thùng, không đẩy hai thùng cùng lúc.
- Mục tiêu: mọi thùng nằm trên ô đích. Có thể có nhiều ô đích hơn thùng.
- **Mỗi lần di chuyển một robot tính một bước**, kể cả đi bộ hoặc đẩy thùng.
  Chất lượng lời giải tính theo tổng số bước, không chỉ số lần đẩy.

Tọa độ `(x, y)` tăng sang phải và xuống dưới. `robots` là tuple theo chỉ số
robot; `boxes`, `storage`, `obstacles` là frozenset tọa độ;
`width`, `height` là kích thước bàn chơi.

## 3. Giao diện cần triển khai

```python
def solve(initial_state, timebound=120):
    ...
```

Đầu vào là một `SokobanState` hợp lệ, có `gval=0`, `parent=None`.
`timebound` là ngân sách chạy tính bằng giây. 

Hàm cần trả về trạng thái đích, sao cho lần ngược theo chuỗi `parent`, `action`,`gval` từ trạng thái đó sẽ cho ra đúng đường đi hợp lệ từ trạng thái ban đầu. Nếu chưa tìm ra lời giải, phải trả đúng giá trị `False`. Một điều quan trọng nữa: không được thay đổi trạng thái đầu vào.

| API có sẵn | Ý nghĩa |
| --- | --- |
| `state.successors()` | Các trạng thái kế hợp lệ, đã gán `parent`, `action`, `gval` |
| `state.hashable_state()` | Khóa cấu hình trong cùng một map |
| `sokoban_goal_state(state)` | Kiểm tra mọi thùng đã ở đích |
| `state.gval` | Tổng số bước từ trạng thái đầu |
| `state.print_state()`, `state.print_path()` | Hiển thị trạng thái, đường đi |



Chạy kiểm tra:
```text
python -m unittest test_framework
python autograder.py
```


## 4. Chấm điểm

Bài được chấm trên **Tập test ẩn** mỗi test có giới hạn thời gian mặc định chạy độc lập trong cùng môi trường chấm. Timeout, crash sẽ tính là fail. Kết quả chấm dựa vào số case pass và đường đi tìm được.


