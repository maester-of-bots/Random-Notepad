import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, font
from openai import OpenAI
from fpdf import FPDF
import subprocess
import requests

class Notepad:
    def __init__(self, root):
        self.root = root
        root.title("Notepad")
        root.geometry("1200x800")
        root.iconbitmap('img/default.ico')

        # Create a menu bar
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save as PDF", command=self.save_as_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        edit_menu.add_command(label="Cut", command=lambda: root.focus_get().event_generate('<<Cut>>'))
        edit_menu.add_command(label="Copy", command=lambda: root.focus_get().event_generate('<<Copy>>'))
        edit_menu.add_command(label="Paste", command=lambda: root.focus_get().event_generate('<<Paste>>'))
        edit_menu.add_command(label="Find and Replace", command=self.find_and_replace)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)

        # Options menu
        options_menu = tk.Menu(self.menu_bar, tearoff=0)
        options_menu.add_command(label="Change Font", command=self.change_font)
        options_menu.add_command(label="Toggle Read-Only", command=self.toggle_read_only)
        self.menu_bar.add_cascade(label="Options", menu=options_menu)

        # OpenAI Menu.  Must add API key to enable other options.
        self.ai_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.ai_menu.add_command(label="Complete this paragraph", command=self.completion, state=tk.DISABLED)
        self.ai_menu.add_command(label="Illustrate", command=self.render_image, state=tk.DISABLED)
        # ai_menu.add_command(label="Show Queue", command=self.create_secondary_window)
        self.ai_menu.add_command(label="Improve highlighted", command=self.improve, state=tk.DISABLED)
        self.ai_menu.add_command(label="Add key", command=self.login)
        self.menu_bar.add_cascade(label="AI", menu=self.ai_menu)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        # Text area
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Arial", 12))
        self.text_area.pack(expand=True, fill=tk.BOTH)
        self.text_area.bind('<KeyRelease>', self.update_status)

        # Status bar
        self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initialize font
        self.current_font = font.Font(family="Arial", size=12)

        # Initialize variable for OpenAI client
        self.client = None

        # Loop for async, not used
        self.loop = None


    def enable_menu_items(self):
        """Enable all the menu items under the AI menu, once the user has input their OpenAI key."""

        for index in range(self.ai_menu.index("end")):
            self.ai_menu.entryconfig(index, state=tk.NORMAL)


    def popup_confirm(self, title, text, button_text="OK"):
        """A popup notification for when the user's key doesn't work."""

        # Create a top-level window
        popup = tk.Toplevel(root)
        popup.title(title)

        # Set the message
        message_label = tk.Label(popup, text=text, font=("Arial", 12))
        message_label.pack(pady=10)

        # Create an OK button
        ok_button = tk.Button(popup, text=button_text, command=popup.destroy)
        ok_button.pack(pady=5)

        # Center the popup window
        root.update_idletasks()
        x = root.winfo_x() + root.winfo_width() // 2 - popup.winfo_width() // 2
        y = root.winfo_y() + root.winfo_height() // 2 - popup.winfo_height() // 2
        popup.geometry(f"+{x}+{y}")

    def login(self):
        """Get the user's OpenAI key and see if we can list the API models.  If this fails, the key is not valid."""

        find_text = simpledialog.askstring("OpenAI Key", "Type in your OpenAI API key here.")

        # Initialize OpenAI client with the API key
        self.client = OpenAI(api_key=find_text)

        # Test the API key.  If it works, enable the other AI options.  Othewise, throw a popup.
        try:
            self.client.models.list()
            self.enable_menu_items()
        except:
            self.popup_confirm('Can\'t communicate with API', "That API key does not seem to be valid.")


    def render_image(self):
        """Use OpenAI DALLE-3 to generate an image based on the text in the notepad"""

        data = self.text_area.get(1.0, tk.END)

        try:

            image_resp = self.client.images.generate(
                model="dall-e-3",
                prompt=data,
            )

            # Grab the URL out of the response
            image_url = image_resp.data[0].url

            # Download the image
            data = requests.get(image_url)

            # Save the image
            with open(f"{image_resp.created}.png",'wb') as image:
                image.write(data.content)

            # Open it
            subprocess.call(['start', f"{image_resp.created}.png"], shell=True)

        except Exception as e:
            if "Your request was rejected as a result of our safety system" in str(e):
                self.popup_confirm('Rejected!','Your request was rejected as a result of our safety system')
            else:
                print(e)


    def improve(self):
        """Use OpenAI to improve the selected text"""

        # Grab the selected text
        data = self.text_area.selection_get()

        # Submit the request to the API
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"Improve this text and respond back with only it"
                },
                {
                    "role": "user",
                    "content": data
                }
            ],
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # Get the text
        final = response.choices[0].message.content

        # Start / End point of the selected text
        start_index = self.text_area.index("sel.first")
        end_index = self.text_area.index("sel.last")

        # Delete the selected text
        self.text_area.delete(start_index, end_index)

        # Insert the new text at the start position of the deleted text
        self.text_area.insert(start_index, final)


    def completion(self):
        """ Use the text in the notepad as a seed and have OpenAI complete it. """

        # Get the text thats written
        data = self.text_area.get(1.0, tk.END)

        # Send it to OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"Complete this text: {data}"
                },
                {
                    "role": "user",
                    "content": ""
                }
            ],
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # Grab the response
        final = response.choices[0].message.content

        # Dump it to the notepad
        self.text_area.insert(tk.END, final)

    def new_file(self):
        """Kill contents of the notepad"""

        self.text_area.delete(1.0, tk.END)

    def open_file(self):
        """Open a file"""

        file_path = filedialog.askopenfilename()
        if file_path:
            with open(file_path, 'r') as file:
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(1.0, file.read())

    def save_file(self):
        """Save the text file"""

        file_path = filedialog.asksaveasfilename()
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.text_area.get(1.0, tk.END))

    def save_as_pdf(self):
        """Save the text as a PDF.  Nifty, right?"""

        file_path = filedialog.asksaveasfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            text = self.text_area.get(1.0, tk.END)
            pdf.multi_cell(0, 10, text)
            pdf.output(file_path)

    def find_and_replace(self):
        """Basic find/replace dialog box"""

        find_text = simpledialog.askstring("Find", "Enter text to find:")
        replace_text = simpledialog.askstring("Replace", "Enter text to replace:")
        if find_text and replace_text:
            content = self.text_area.get(1.0, tk.END)
            new_content = content.replace(find_text, replace_text)
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(1.0, new_content)

    def update_status(self, event=None):
        lines = int(self.text_area.index('end-1c').split('.')[0])
        chars = int(self.text_area.index('end-1c').split('.')[1])
        self.status_bar.config(text=f"Lines: {lines} Chars: {chars}")

    def change_font(self):
        new_font = simpledialog.askstring("Font", "Enter font name:")
        new_size = simpledialog.askinteger("Size", "Enter font size:", minvalue=1, maxvalue=100)
        if new_font and new_size:
            self.current_font.config(family=new_font, size=new_size)
            self.text_area.config(font=self.current_font)

    def toggle_read_only(self):
        if self.text_area['state'] == 'normal':
            self.text_area['state'] = 'disabled'
        else:
            self.text_area['state'] = 'normal'

    def show_about(self):
        messagebox.showinfo("About", "Made with Python.  https://github.com/maester-of-bots/Random-Notepad")


if __name__ == "__main__":
    root = tk.Tk()
    app = Notepad(root)

    # Start the Tkinter main loop
    root.mainloop()
