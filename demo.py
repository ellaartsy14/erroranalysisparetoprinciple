#download the following packages
#pip install pylint
#pip install pandas
#pip install matplotlib

import subprocess
import re
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
import json 
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
from matplotlib.ticker import PercentFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

filess = None

# Function to open file dialog and select files
def select_files():
    global filess
    file_paths = filedialog.askopenfilenames(title="Select Python Files", filetypes=[("Python Files", "*.py")])
    filess = list(file_paths)
    show_selected_files()

def show_selected_files():
    selected_files_text.delete(1.0, tk.END)
    if filess:
        for file in filess:
            selected_files_text.insert(tk.END, file + "\n")
    else:
        selected_files_text.insert(tk.END, "No files selected.")

def run_analysis():
    if not filess:
        print("No files selected. Exiting.")
        return

    python_files = filess

    # Run Pyright on the selected python files and write the output to a log file
    pyright_log_file = "pyright_log.txt"
    with open(pyright_log_file, 'w', encoding='utf-8') as f:
        for python_file in python_files:
            result = subprocess.run(["pyright", "--outputjson", python_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            f.write(result.stdout)
            f.write(result.stderr)

    # Run Pylint on the selected python files and write the output to a log file
    pylint_log_file = "pylint_log.txt"
    with open(pylint_log_file, 'w', encoding='utf-8') as f:
        for python_file in python_files:
            result = subprocess.run(["pylint", "--exit-zero", "--output-format=text", python_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            f.write(result.stdout)
            f.write(result.stderr)

    # Error codes for Pylint
    pylint_error_codes = [ ]

    # Count the number of errors in each category
    error_counts = {'Error': 0}
    category_counts = {category: 0 for category in pylint_error_codes.keys()}
    category_counts['Error'] = 0

    # Count the number of errors in each category by finding the error codes in the Pyright log file
    with open(pyright_log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
        error_counts['Error'] = len(re.findall(r'\berror\b', log_content))
        category_counts['Error'] = error_counts['Error']
        y = json.loads(log_content)
        for i in y["generalDiagnostics"]:
            print(i["rule"])
    # Count the number of errors in each category by finding the error codes in the Pylint log file
    with open(pylint_log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
        for code in pylint_error_codes:
            for error_code in pylint_error_codes[code]:
                count = len(re.findall(r'\b' + re.escape(error_code) + r'\b', log_content))
                category_counts[code] += count


    # Dataframe of the error categories for the pareto chart
    df = pd.DataFrame({'Analysis': [category_counts['Fatal'], category_counts['Error'], category_counts['Warning'], category_counts['Convention'], category_counts['Refactor']]})
    df.index = ['Fatal', 'Error', 'Warning', 'Convention', 'Refactor']
    df = df.sort_values(by='Analysis', ascending=False)
    df["cumpercentage"] = df["Analysis"].cumsum()/df["Analysis"].sum()* 100

    # Show the pareto chart
    def show_chart():
        fig, ax1 = plt.subplots()
        fig.patch.set_facecolor('#333333')  # Set the background color of the figure
        ax1.set_facecolor('#444444')  # Set the background color of the axes
        ax1.bar(df.index, df["Analysis"], color="C0")
        ax1.set_ylabel("Number of Errors", color="C0")
        ax1.tick_params(axis="y", colors="C0")
        ax1.set_xlabel("Error Category")
        ax1.set_xticklabels(df.index, rotation=45)
        ax1.set_title("Pareto Chart of Error Categories")
        ax2 = ax1.twinx()
        ax2.plot(df.index, df["cumpercentage"], color="C1", marker="D", ms=7)
        ax2.yaxis.set_major_formatter(PercentFormatter())
        ax2.tick_params(axis="y", colors="C1")
        # Add the chart to the chart frame
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Find the top errors contributing to 80% of the issues
    df_pareto = df[df["cumpercentage"] <= 80]

    # If the dataframe is empty, use the first row
    if df_pareto.empty:
        df_pareto = df.iloc[:1]

    # Display the top errors contributing to 80% of the issues
    df_pareto_category = df_pareto.index.tolist()
    final_analysis = [category[0] for category in df_pareto_category]
    print("\nTop Errors Contributing to 80% of Issues:")
    print(final_analysis)

    # Display the feedback for the errors causing 80% of the issues
    relevant_errors = df_pareto.index.tolist()
    print("\nFeedbacks for errors causing 80% of the issues:")
    feedbacks_by_module = {}

    # Find the error codes in the log file and display the feedback
    for error in relevant_errors:
        if error == 'Error':
            with open(pyright_log_file, 'r', encoding='utf-8') as f:
                log_content = f.readlines()
                for line in log_content:
                    if 'error' in line:
                        match = re.search(r'(\w+\.py):(\d+):(\d+): (error): (.+)', line)
                        if match:
                            module_name = match.group(1)
                            line_number = match.group(2)
                            column_number = match.group(3)
                            error_message = match.group(5)
                            if module_name not in feedbacks_by_module:
                                feedbacks_by_module[module_name] = []
                            feedbacks_by_module[module_name].append(f"Line {line_number} : {error_message}")
                            print(feedbacks_by_module[module_name].append(f"Line {line_number} : {error_code}: {error_message}"))
        else:
            with open(pylint_log_file, 'r', encoding='utf-8') as f:
                log_content = f.readlines()
                for line in log_content:
                    if any(code in line for code in pylint_error_codes[error]):
                        match = re.search(r'(\w+\.py):(\d+):\d+: (\w\d+): (.+)', line)
                        if match:
                            module_name = match.group(1)
                            line_number = match.group(2)
                            error_code = match.group(3)
                            error_message = match.group(4)
                            if module_name not in feedbacks_by_module:
                                feedbacks_by_module[module_name] = []
                            print(feedbacks_by_module[module_name].append(f"Line {line_number} : {error_code}: {error_message}"))

    # Apply Pareto's principle to the feedback
    feedback_text = ""
    total_issues = sum(category_counts.values())
    accumulated_percentage = 0

    for category in df.index:
        category_percentage = (category_counts[category] / total_issues) * 100
        if accumulated_percentage + category_percentage > 80:
            remaining_percentage = 80 - accumulated_percentage
            feedback_text += f"\n{category} (Partial - {remaining_percentage:.2f}%):\n"
            for module_name, feedbacks in feedbacks_by_module.items():
                if category in module_name:
                    feedback_text += f"\n({module_name})\n"
                    for feedback in feedbacks[:int(len(feedbacks) * (remaining_percentage / category_percentage))]:
                        feedback_text += feedback + "\n\n"
            accumulated_percentage = 80
            break
        else:
            feedback_text += f"\n{category} ({category_percentage:.2f}%):\n"
            for module_name, feedbacks in feedbacks_by_module.items():
                if category in module_name:
                    feedback_text += f"\n({module_name})\n"
                    for feedback in feedbacks:
                        feedback_text += feedback + "\n\n"
            accumulated_percentage += category_percentage

    # Update the GUI with the chart and feedbacks
    update_gui(feedback_text)
    show_chart()

def update_gui(feedback_text):
    # Clear previous content
    for widget in feedback_frame.winfo_children():
        widget.destroy()

    # Add the feedbacks to the feedback frame
    feedback_label = tk.Label(feedback_frame, text="Feedbacks", font=("Arial", 20), bg='#333333', fg='#FFFFFF')
    feedback_label.pack(pady=10)
    feedback_text_widget = ScrolledText(feedback_frame, wrap=tk.WORD, font=("Arial", 12), bg='#333333', fg='#FFFFFF')
    feedback_text_widget.pack(fill=tk.BOTH, expand=True)
    feedback_text_widget.insert(tk.END, feedback_text)

# Create the main window
root = tk.Tk()
root.title("Pyright and Pylint Analysis")
root.geometry("1200x800")
root.configure(bg='#333333')

# Create a title label
title_label = tk.Label(root, text="Pyright and Pylint Analysis Tool", font=("Arial", 24), bg='#333333', fg='#FF3399')
title_label.pack(pady=20)

# Create a frame for the buttons and selected files
control_frame = tk.Frame(root, bg='#333333')
control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

# Create a button to select files
select_files_button = tk.Button(control_frame, text="Select Files", font=("Arial", 16), command=select_files, bg='#FF3399', fg='#FFFFFF')
select_files_button.pack(side=tk.LEFT, padx=10)

# Create a button to run the analysis
run_analysis_button = tk.Button(control_frame, text="Run Analysis", font=("Arial", 16), command=lambda: threading.Thread(target=run_analysis).start(), bg='#FF3399', fg='#FFFFFF')
run_analysis_button.pack(side=tk.LEFT, padx=10)
 
# Create a ScrolledText widget to display selected files
selected_files_text = ScrolledText(control_frame, wrap=tk.WORD, font=("Arial", 12), height=5, bg='#333333', fg='#FFFFFF')
selected_files_text.pack(fill=tk.X, pady=10)

# Create a frame for the chart
chart_frame = tk.Frame(root, bg='#333333')
chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Create a frame for the feedbacks
feedback_frame = tk.Frame(root, bg='#333333')
feedback_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Start the Tkinter main loop
root.mainloop()