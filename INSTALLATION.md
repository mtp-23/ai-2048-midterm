# Hướng dẫn cài đặt

Project không bắt buộc Conda. Sinh viên chỉ cần Python 3.10 trở lên và các thư
viện trong `requirements.txt`.

## 1. Kiểm tra Python

Mở PowerShell tại thư mục project và chạy:

```powershell
python --version
python -m pip --version
```

Nếu máy không nhận lệnh `python`, cài Python từ trang chính thức và bật tùy
chọn **Add Python to PATH** trong quá trình cài.

## 2. Cài project

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

- Lệnh đầu cài dependency cần thiết như NumPy và pytest.
- Lệnh thứ hai cài package `game2048` ở chế độ editable.
- UI dùng Tkinter, thường có sẵn trong bộ cài Python trên Windows.

Kiểm tra:

```powershell
python -c "import game2048, numpy, tkinter; print('Cài đặt thành công')"
python -m pytest -q
```

## 3. Virtual environment — không bắt buộc

Nếu muốn tách thư viện của project khỏi Python hệ thống:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

Thoát môi trường bằng `deactivate`. Có thể dùng Conda thay cho `venv`, nhưng
tên môi trường không quan trọng và không ảnh hưởng việc chấm.

## 4. Chạy lần đầu

```powershell
python scripts/play.py --seed 42
python scripts/benchmark_agent.py --agent student.agent:Agent --seeds 1 --start-seed 42 --total-time-sec 5
```

## 5. Lỗi thường gặp

### `ModuleNotFoundError: game2048`

Đảm bảo đang đứng tại thư mục gốc rồi chạy:

```powershell
python -m pip install -e .
```

### `ModuleNotFoundError: student`

Chạy script tại thư mục gốc, không chạy từ bên trong thư mục `student/`.

### Không import được Tkinter

```powershell
python -c "import tkinter; print(tkinter.TkVersion)"
```

Trên Windows, sửa/cài lại Python với thành phần **Tcl/Tk and IDLE**. Trên
Ubuntu/Debian có thể cần package hệ thống `python3-tk`. Benchmark vẫn chạy được
trên máy không có desktop.

### PowerShell chặn kích hoạt `.venv`

Có thể dùng Python trong môi trường mà không cần activate:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\play.py
```

### Cài đúng thư viện nhưng vẫn import sai

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
```

Luôn dùng `python -m pip` thay vì gọi `pip` trực tiếp để tránh cài nhầm vào một
Python khác.
