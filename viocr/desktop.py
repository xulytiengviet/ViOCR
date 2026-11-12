"""ViOCR for desktop. Open a document to recognize it; export via Save As."""
import json
from pathlib import Path
import queue
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from docx import Document
from run import convert

MODES = {'Tiếng Việt Unicode': 'unicode', 'CVNSS4.0': 'cvss', 'Số nguyên Base27': 'base27'}


def save_pages(path, texts, kind):
    if kind == 'docx':
        document = Document()
        document.core_properties.author = 'Long Ngo'
        for i, text in enumerate(texts):
            if i:
                document.add_page_break()
            for line in text.split('\n'):
                document.add_paragraph(line)
        document.save(path)
    else:
        Path(path).write_text('\n\f\n'.join(texts), encoding='utf-8-sig')


class App:
    def __init__(self, root):
        self.root = root
        root.title('ViOCR · Long Ngo')
        root.geometry('780x530')
        self.messages = queue.Queue()
        self.mode = tk.StringVar(value=next(iter(MODES)))
        self.status = tk.StringVar(value='Chọn ảnh hoặc PDF để bắt đầu.')
        tk.Label(root, text='ViOCR   /   Nhận dạng tài liệu', bg='#12375d', fg='white',
                 anchor='w', padx=10, pady=5, font=('Tahoma', 11, 'bold')).pack(fill='x')
        bar = tk.Frame(root, padx=10, pady=10)
        bar.pack(fill='x')
        self.open = tk.Button(bar, text='Mở tài liệu…', command=self.choose)
        self.open.pack(side='left')
        self.select = ttk.Combobox(bar, values=list(MODES), textvariable=self.mode, state='readonly')
        self.select.pack(side='right')
        self.view = tk.Text(root, font=('Consolas', 11), wrap='word', bg='#fffef8', state='disabled')
        self.view.pack(fill='both', expand=True, padx=10)
        actions = tk.Frame(root, padx=10, pady=8)
        actions.pack(fill='x')
        self.buttons = []
        for label, kind in [('Lưu Word (.docx)…', 'docx'), ('Lưu TXT…', 'txt')]:
            btn = tk.Button(actions, text=label, command=lambda k=kind: self.save(k), state='disabled')
            btn.pack(side='left', padx=2)
            self.buttons.append(btn)
        tk.Label(root, textvariable=self.status, anchor='w', relief='sunken').pack(fill='x')
        self.root.after(100, self.poll)

    def choose(self):
        path = filedialog.askopenfilename(filetypes=[('Ảnh và PDF', '*.pdf *.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff *.gif *.avif'), ('Mọi tệp', '*.*')])
        if not path:
            return
        self.path = Path(path)
        self.texts = []
        self.show('')
        self.open.configure(state='disabled')
        self.select.configure(state='disabled')
        for button in self.buttons:
            button.configure(state='disabled')
        self.status.set('Đang nhận dạng ' + self.path.name + '…')
        threading.Thread(target=self.read, args=(self.path, MODES[self.mode.get()]), daemon=True).start()

    def read(self, path, mode):
        try:
            with tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / 'output.jsonl'
                convert(path, output, mode, 150)
                texts = [json.loads(s)['text'] for s in output.read_text(encoding='utf8').splitlines()]
            self.messages.put((texts, None))
        except Exception as exc:
            detail = getattr(exc, 'stderr', None)
            self.messages.put(([], detail.decode('utf8', 'replace') if detail else str(exc)))

    def show(self, text):
        self.view.configure(state='normal')
        self.view.delete('1.0', 'end')
        self.view.insert('1.0', text)
        self.view.configure(state='disabled')

    def poll(self):
        try:
            self.texts, error = self.messages.get_nowait()
        except queue.Empty:
            pass
        else:
            self.open.configure(state='normal')
            self.select.configure(state='readonly')
            if error:
                self.status.set('Không đọc được tài liệu.')
                messagebox.showerror('ViOCR', error)
            else:
                self.show('\n\n'.join(self.texts))
                self.status.set(f'{self.path.name} · {len(self.texts)} trang' if any(self.texts) else 'Không tìm thấy chữ.')
                for button in self.buttons:
                    button.configure(state='normal')
        self.root.after(100, self.poll)

    def save(self, kind):
        path = filedialog.asksaveasfilename(defaultextension='.' + kind, initialfile=self.path.stem + '.' + kind,
                                            filetypes=[(kind.upper(), '*.' + kind)])
        if path:
            try:
                save_pages(path, self.texts, kind)
                self.status.set('Đã lưu ' + path)
            except OSError as exc:
                messagebox.showerror('Lỗi lưu tệp', str(exc))


if __name__ == '__main__':
    window = tk.Tk()
    App(window)
    window.mainloop()
