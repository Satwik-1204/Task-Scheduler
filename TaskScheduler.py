import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Text
from tkcalendar import Calendar
from datetime import datetime, timedelta
import json
import os
import subprocess
from plyer import notification
import threading
import time
import heapq
import logging

TASKS_FILE = "tasks.json"
LOG_FILE = "executed_tasks.txt"
DEBUG_LOG = "scheduler_debug.log"

logging.basicConfig(filename=DEBUG_LOG, level=logging.DEBUG, format="%(asctime)s - %(message)s")

class TaskSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Scheduler")
        self.root.geometry("600x600")
        self.root.configure(bg="#2e2e2e")

        self.tasks = self.load_tasks()
        self.task_queue = []
        self.notification_thread = None
        self.running = True
        self.priority_map = {"High": 1, "Medium": 2, "Low": 3}

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#2e2e2e", foreground="white", font=("Times New Roman", 12))
        self.style.configure("TButton", background="#4a4a4a", foreground="white", font=("Times New Roman", 12))
        self.style.configure("TEntry", fieldbackground="#4a4a4a", foreground="white", font=("Times New Roman", 12))
        self.style.configure("TCombobox", fieldbackground="#4a4a4a", foreground="white", font=("Times New Roman", 12))
        self.style.configure("Treeview", background="#4a4a4a", foreground="white", fieldbackground="#4a4a4a", font=("Times New Roman", 11))
        self.style.configure("Treeview.Heading", background="#4a4a4a", foreground="white", font=("Times New Roman", 12))
        self.style.map("TButton", background=[("active", "#6b6b6b")])
        self.style.map("TCombobox", fieldbackground=[("active", "#6b6b6b")])

        ttk.Label(root, text="Task Title:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.title_entry = ttk.Entry(root, width=40)
        self.title_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(root, text="Task Description:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.desc_text = Text(root, height=4, width=40, bg="#4a4a4a", fg="white", font=("Times New Roman", 12), insertbackground="white")
        self.desc_text.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(root, text="Attach Files:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.file_list = []
        self.file_label = ttk.Label(root, text="No files selected")
        self.file_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.add_file_button = ttk.Button(root, text="Add File", command=self.add_file)
        self.add_file_button.grid(row=2, column=1, padx=10, pady=5, sticky="e")

        ttk.Label(root, text="Due Date:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.cal = Calendar(root, selectmode="day", date_pattern="yyyy-mm-dd", background="#4a4a4a", foreground="white", selectbackground="#6b6b6b", font=("Times New Roman", 12))
        self.cal.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(root, text="Due Time:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.time_frame = ttk.Frame(root)
        self.time_frame.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.hour_spin = ttk.Spinbox(self.time_frame, from_=0, to=23, width=5, format="%02.0f")
        self.hour_spin.grid(row=0, column=0)
        ttk.Label(self.time_frame, text=":").grid(row=0, column=1)
        self.minute_spin = ttk.Spinbox(self.time_frame, from_=0, to=59, width=5, format="%02.0f")
        self.minute_spin.grid(row=0, column=2)

        ttk.Label(root, text="Priority:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.priority_var = tk.StringVar(value="Medium")
        self.priority_menu = ttk.Combobox(root, textvariable=self.priority_var, values=["High", "Medium", "Low"], state="readonly")
        self.priority_menu.grid(row=5, column=1, padx=10, pady=5, sticky="w")

        self.add_button = ttk.Button(root, text="Add Task", command=self.add_task)
        self.add_button.grid(row=6, column=0, padx=5, pady=10)

        self.test_notification_button = ttk.Button(root, text="Test Notification", command=self.test_notification)
        self.test_notification_button.grid(row=6, column=1, padx=5, pady=10, sticky="e")

        self.task_tree = ttk.Treeview(root, columns=("S.No", "Task", "Due Date", "Due Time", "Priority", "Status"), show="headings")
        self.task_tree.heading("S.No", text="S.No")
        self.task_tree.heading("Task", text="Task")
        self.task_tree.heading("Due Date", text="Due Date")
        self.task_tree.heading("Due Time", text="Due Time")
        self.task_tree.heading("Priority", text="Priority")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.column("S.No", width=50, anchor="center")
        self.task_tree.column("Task", width=150)
        self.task_tree.column("Due Date", width=100)
        self.task_tree.column("Due Time", width=80)
        self.task_tree.column("Priority", width=80)
        self.task_tree.column("Status", width=80)
        self.task_tree.grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.task_tree.bind("<Double-1>", self.show_task_details)
        self.task_tree.bind("<Button-3>", self.show_file_menu)

        self.complete_button = ttk.Button(root, text="Mark as Completed", command=self.mark_completed)
        self.complete_button.grid(row=8, column=0, padx=5, pady=5)
        self.delete_button = ttk.Button(root, text="Delete Task", command=self.delete_task)
        self.delete_button.grid(row=8, column=1, padx=5, pady=5)

        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(7, weight=1)

        self.rebuild_priority_queue()

        self.refresh_task_list()

        self.notification_thread = threading.Thread(target=self.check_notifications, daemon=True)
        self.notification_thread.start()

    def add_file(self):
        files = filedialog.askopenfilenames(filetypes=[("All files", "*.*")])
        self.file_list.extend(files)
        self.file_label.config(text=f"{len(self.file_list)} file(s) selected")
        logging.info(f"Selected {len(files)} file(s) for attachment")
        print(f"Selected {len(files)} file(s) for attachment")

    def show_task_details(self, event):
        item = self.task_tree.identify("item", event.x, event.y)
        column = self.task_tree.identify_column(event.x)
        if not item or column != "#2":
            return
        task_index = int(self.task_tree.index(item))
        task = self.tasks[task_index]

        details_window = tk.Toplevel(self.root)
        details_window.title(f"Task Details: {task['name']}")
        details_window.geometry("400x500")
        details_window.configure(bg="#2e2e2e")

        ttk.Label(details_window, text=f"Title: {task['name']}", font=("Times New Roman", 14, "bold")).pack(pady=5)
        ttk.Label(details_window, text=f"Due Date: {task['due_date']}").pack(pady=5)
        ttk.Label(details_window, text=f"Due Time: {task['due_time']}").pack(pady=5)
        ttk.Label(details_window, text=f"Priority: {task['priority']}").pack(pady=5)
        ttk.Label(details_window, text=f"Status: {task['status']}").pack(pady=5)
        ttk.Label(details_window, text="Description:", font=("Times New Roman", 12, "bold")).pack(pady=5, anchor="w", padx=10)
        desc_text = Text(details_window, height=5, width=40, bg="#4a4a4a", fg="white", font=("Times New Roman", 12), wrap="word")
        desc_text.insert("1.0", task.get("description", ""))
        desc_text.config(state="disabled")
        desc_text.pack(pady=5, padx=10)

        ttk.Label(details_window, text="Attached Files:", font=("Times New Roman", 12, "bold")).pack(pady=5, anchor="w", padx=10)
        if task.get("files", []):
            for file_path in task["files"]:
                file_name = os.path.basename(file_path)
                btn = ttk.Button(details_window, text=file_name, command=lambda fp=file_path: self.open_file(fp))
                btn.pack(pady=2, padx=10, anchor="w")
        else:
            ttk.Label(details_window, text="No files attached").pack(pady=5, padx=10, anchor="w")
        logging.info(f"Opened details for task: {task['name']}")
        print(f"Opened details for task: {task['name']}")

    def open_file(self, file_path):
        try:
            if os.path.exists(file_path):
                subprocess.run(["start", "", file_path], shell=True, check=True)
                logging.info(f"Opened file: {file_path}")
                print(f"Opened file: {file_path}")
            else:
                messagebox.showerror("Error", f"File not found: {file_path}")
                logging.error(f"File not found: {file_path}")
                print(f"Error: File not found: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
            logging.error(f"Failed to open file: {str(e)}")
            print(f"Error: Failed to open file: {str(e)}")

    def show_file_menu(self, event):
        item = self.task_tree.identify("item", event.x, event.y)
        if not item:
            return
        task_index = int(self.task_tree.index(item))
        task = self.tasks[task_index]
        self.file_menu = tk.Menu(self.root, tearoff=0)
        files = task.get("files", [])
        if files:
            for file_path in files:
                file_name = os.path.basename(file_path)
                self.file_menu.add_command(label=file_name, command=lambda fp=file_path: self.open_file(fp))
        else:
            self.file_menu.add_command(label="No files attached", state="disabled")
        self.file_menu.post(event.x_root, event.y_root)
        logging.info(f"Opened file menu for task: {task['name']}")
        print(f"Opened file menu for task: {task['name']}")

    def load_tasks(self):
        try:
            if os.path.exists(TASKS_FILE):
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                    valid_tasks = []
                    required_keys = {"name", "due_date", "due_time", "status", "priority"}
                    for task in tasks:
                        if not isinstance(task, dict):
                            continue
                        if not all(key in task for key in required_keys):
                            continue
                        if not isinstance(task["name"], str) or not task["name"].strip():
                            continue
                        if task["status"] not in ["Pending", "Completed"]:
                            continue
                        if task["priority"] not in ["High", "Medium", "Low"]:
                            continue
                        if not isinstance(task.get("description", ""), str):
                            task["description"] = ""
                        if not isinstance(task.get("files", []), list):
                            task["files"] = []
                        try:
                            datetime.strptime(f"{task['due_date']} {task['due_time']}", "%Y-%m-%d %H:%M")
                            valid_tasks.append(task)
                        except ValueError:
                            logging.error(f"Invalid date/time for task: {task}")
                            print(f"Error: Invalid date/time for task: {task}")
                            continue
                    logging.info(f"Loaded {len(valid_tasks)} valid tasks")
                    print(f"Loaded {len(valid_tasks)} tasks from {TASKS_FILE}")
                    return valid_tasks
            return []
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to load tasks: Invalid JSON format")
            logging.error("Failed to load tasks: Invalid JSON format")
            print("Error: Failed to load tasks due to invalid JSON format")
            return []
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tasks: {str(e)}")
            logging.error(f"Failed to load tasks: {str(e)}")
            print(f"Error: Failed to load tasks: {str(e)}")
            return []

    def save_tasks(self):
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=4)
            logging.info("Tasks saved successfully")
            print(f"Saved tasks to {TASKS_FILE}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save tasks: {str(e)}")
            logging.error(f"Failed to save tasks: {str(e)}")
            print(f"Error: Failed to save tasks: {str(e)}")

    def log_task(self, task):
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{log_time}] Completed: {task['name']} (Due: {task['due_date']} {task['due_time']}, Priority: {task['priority']})\n")
            logging.info(f"Logged completed task: {task['name']}")
            print(f"Logged completed task: {task['name']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to log task: {str(e)}")
            logging.error(f"Failed to log task: {str(e)}")
            print(f"Error: Failed to log task: {str(e)}")

    def rebuild_priority_queue(self):
        self.task_queue = []
        for idx, task in enumerate(self.tasks):
            if task["status"] == "Pending":
                try:
                    due_datetime = datetime.strptime(f"{task['due_date']} {task['due_time']}", "%Y-%m-%d %H:%M")
                    priority_num = self.priority_map[task["priority"]]
                    heapq.heappush(self.task_queue, (priority_num, due_datetime, idx))
                except ValueError:
                    logging.error(f"Failed to add task to queue: {task}")
                    print(f"Error: Failed to add task to queue: {task}")
                    continue
        logging.info(f"Rebuilt priority queue with {len(self.task_queue)} tasks")
        print(f"Rebuilt priority queue with {len(self.task_queue)} tasks")

    def add_task(self):
        task_name = self.title_entry.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        due_date = self.cal.get_date()
        due_time = f"{self.hour_spin.get().zfill(2)}:{self.minute_spin.get().zfill(2)}"
        priority = self.priority_var.get()
        files = self.file_list[:]

        if not task_name:
            messagebox.showwarning("Warning", "Task title cannot be empty")
            logging.info("Task title empty")
            print("Warning: Task title cannot be empty")
            return

        try:
            due_datetime = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            task = {
                "name": task_name,
                "description": description,
                "due_date": due_date,
                "due_time": due_time,
                "priority": priority,
                "status": "Pending",
                "files": files
            }
            self.tasks.append(task)
            self.save_tasks()
            self.rebuild_priority_queue()
            self.refresh_task_list()
            self.title_entry.delete(0, tk.END)
            self.desc_text.delete("1.0", tk.END)
            self.file_list.clear()
            self.file_label.config(text="No files selected")
            logging.info(f"Added task: {task_name}, Due: {due_date} {due_time}")
            print(f"Added task: {task_name}, Due: {due_date} {due_time}")
            time_diff_seconds = (due_datetime - datetime.now()).total_seconds()
            time_diff_hours = time_diff_seconds / 3600
            logging.info(f"Task {task_name} time diff: {time_diff_seconds} seconds")
            print(f"Task {task_name} time diff: {time_diff_seconds} seconds")
            if time_diff_seconds <= 0:
                logging.info(f"Task {task_name} is past due, no notification sent")
                print(f"Task {task_name} is past due, no notification sent")
            elif time_diff_hours <= 1:
                try:
                    notification.notify(
                        title="Task Reminder",
                        message=f"Task '{task_name}' (Priority: {priority}) is due soon!",
                        app_name="TaskScheduler",
                        timeout=10
                    )
                    logging.info(f"Immediate 1-hour notification sent for task: {task_name}")
                    print(f"Immediate 1-hour notification sent for task: {task_name}")
                except Exception as e:
                    logging.error(f"Failed to send immediate notification for {task_name}: {str(e)}")
                    print(f"Error: Failed to send immediate notification for {task_name}: {str(e)}")
                    messagebox.showerror("Notification Error", f"Failed to send notification: {str(e)}")
        except ValueError:
            messagebox.showwarning("Warning", "Invalid date or time format")
            logging.error(f"Invalid date/time format: {due_date} {due_time}")
            print(f"Error: Invalid date/time format: {due_date} {due_time}")

    def mark_completed(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task")
            logging.info("No task selected for marking completed")
            print("Warning: Please select a task")
            return

        for item in selected:
            task_index = int(self.task_tree.index(item))
            if self.tasks[task_index]["status"] != "Completed":
                self.tasks[task_index]["status"] = "Completed"
                self.log_task(self.tasks[task_index])
        self.save_tasks()
        self.rebuild_priority_queue()
        self.refresh_task_list()

    def delete_task(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task")
            logging.info("No task selected for deletion")
            print("Warning: Please select a task")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete the selected task(s)?"):
            for item in selected:
                task_index = int(self.task_tree.index(item))
                self.tasks.pop(task_index)
            self.save_tasks()
            self.rebuild_priority_queue()
            self.refresh_task_list()

    def refresh_task_list(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        sorted_tasks = sorted(
            [(self.priority_map[task["priority"]], datetime.strptime(f"{task['due_date']} {task['due_time']}", "%Y-%m-%d %H:%M"), task) for task in self.tasks],
            key=lambda x: (x[0], x[1])
        )
        for idx, (_, _, task) in enumerate(sorted_tasks, 1):
            self.task_tree.insert("", tk.END, values=(idx, task["name"], task["due_date"], task["due_time"], task["priority"], task["status"]))
        logging.info("Task list refreshed")
        print("Task list refreshed")

    def check_notifications(self):
        while self.running:
            current_time = datetime.now()
            logging.info(f"Checking notifications at {current_time}, queue size: {len(self.task_queue)}")
            print(f"Checking notifications at {current_time}, queue size: {len(self.task_queue)}")
            for priority_num, due_datetime, task_index in self.task_queue[:]:
                task = self.tasks[task_index]
                if task["status"] == "Pending":
                    time_diff_seconds = (due_datetime - current_time).total_seconds()
                    time_diff_hours = time_diff_seconds / 3600
                    logging.info(f"Task: {task['name']}, Time diff: {time_diff_seconds} seconds")
                    print(f"Task: {task['name']}, Time diff: {time_diff_seconds} seconds")
                    if time_diff_seconds <= 0:
                        self.task_queue.remove((priority_num, due_datetime, task_index))
                        heapq.heapify(self.task_queue)
                        logging.info(f"Task {task['name']} is past due, removed from queue")
                        print(f"Task {task['name']} is past due, removed from queue")
                    elif 0 < time_diff_hours <= 1:
                        try:
                            notification.notify(
                                title="Task Reminder",
                                message=f"Task '{task['name']}' (Priority: {task['priority']}) is due in 1 hour!",
                                app_name="TaskScheduler",
                                timeout=10
                            )
                            logging.info(f"1-hour notification sent for task: {task['name']}")
                            print(f"1-hour notification sent for task: {task['name']}")
                            self.task_queue.remove((priority_num, due_datetime, task_index))
                            heapq.heapify(self.task_queue)
                        except Exception as e:
                            logging.error(f"Failed to send 1-hour notification for {task['name']}: {str(e)}")
                            print(f"Error: Failed to send 1-hour notification for {task['name']}: {str(e)}")
                            messagebox.showerror("Notification Error", f"Failed to send notification: {str(e)}")
            time.sleep(15)  

    def test_notification(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task to test notification")
            logging.info("No task selected for test notification")
            print("Warning: Please select a task to test notification")
            return
        try:
            task_index = int(self.task_tree.index(selected[0]))
            task = self.tasks[task_index]
            notification.notify(
                title="Test Notification",
                message=f"Test: Task '{task['name']}' (Priority: {task['priority']})",
                app_name="TaskScheduler",
                timeout=10
            )
            logging.info(f"Test notification sent for task: {task['name']}")
            print(f"Test notification sent for task: {task['name']}")
        except Exception as e:
            logging.error(f"Failed to send test notification for {task['name']}: {str(e)}")
            print(f"Error: Failed to send test notification for {task['name']}: {str(e)}")
            messagebox.showerror("Notification Error", f"Failed to send test notification: {str(e)}")

    def on_closing(self):
        self.running = False
        if self.notification_thread:
            self.notification_thread.join(timeout=1.0)
        self.root.destroy()

def main():
    print("Starting Task Scheduler app")
    root = tk.Tk()
    app = TaskSchedulerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()



    