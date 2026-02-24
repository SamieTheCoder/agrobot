import customtkinter as ctk
from PIL import Image
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException, 
    StaleElementReferenceException, 
    NoSuchElementException,
    ElementNotInteractableException,
    WebDriverException
)
from tkinter import filedialog
import threading
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustElementHandler:
    """Handles robust element interactions with retry mechanisms"""
    
    def __init__(self, driver, default_timeout=30):
        self.driver = driver
        self.default_timeout = default_timeout
    
    def safe_find_element(self, locator, timeout=None, retries=3):
        """Safely find element with retries"""
        timeout = timeout or self.default_timeout
        
        for attempt in range(retries):
            try:
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(EC.presence_of_element_located(locator))
                return element
            except (TimeoutException, NoSuchElementException) as e:
                if attempt == retries - 1:
                    logger.error(f"Failed to find element {locator} after {retries} attempts")
                    raise e
                time.sleep(1)
        return None
    
    def safe_click(self, locator, timeout=None, retries=3):
        """Safely click element with retries"""
        timeout = timeout or self.default_timeout
        
        for attempt in range(retries):
            try:
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(EC.element_to_be_clickable(locator))
                element.click()
                return True
            except (StaleElementReferenceException, ElementNotInteractableException, TimeoutException) as e:
                if attempt == retries - 1:
                    logger.error(f"Failed to click element {locator} after {retries} attempts")
                    raise e
                time.sleep(1)
        return False
    
    def safe_send_keys(self, locator, text, clear_first=True, timeout=None, retries=3):
        """Safely send keys to element with retries"""
        timeout = timeout or self.default_timeout
        
        for attempt in range(retries):
            try:
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(EC.element_to_be_clickable(locator))
                
                if clear_first:
                    element.clear()
                    time.sleep(0.1)  # Reduced delay
                
                element.send_keys(str(text))
                return True
            except (StaleElementReferenceException, ElementNotInteractableException, TimeoutException) as e:
                if attempt == retries - 1:
                    logger.error(f"Failed to send keys to element {locator} after {retries} attempts")
                    raise e
                time.sleep(1)
        return False
    
    def wait_for_page_load(self, timeout=30):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(0.5)  # Reduced additional buffer
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Color palette
        self.colors = {
            'primary': "#150016",    
            'secondary': "#150016", 
            'accent': "#676F9D",     
            'success': "#39A284",    
            'warning': "#FFAE6D",    
            'danger': "#FF6B6B",     
            'text': "#F4EEE8" ,      
            'bgcolor': "#522C5D"     
        }

        self.title("Data Drift Automation's")
        self.configure(fg_color=self.colors['bgcolor'])
        self.geometry("1400x800")
        self.minsize(1200, 700)
        self.resizable(True, True)

        # Configure grid weight
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create main scrollable frame
        self.main_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Initialize dictionaries
        self.file_paths = {}
        self.drivers = {}
        self.credential_entries = {}
        self.element_handlers = {}
        self.excel_credentials = {}

        # Welcome labels
        ctk.CTkLabel(
            master=self.main_container,
            text="Data Entry Wizard",
            text_color=self.colors['primary'],
            font=("GoodTimesRg-Regular", 50)
        ).pack(pady=(20, 5))
        
        # Dropdown section
        dropdown_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        dropdown_frame.pack(pady=(20, 30), fill="x")
        
        ctk.CTkLabel(
            master=dropdown_frame,
            text="Number of files to process",
            text_color=self.colors['secondary'],
            font=("Arial Bold", 16),
            corner_radius=10
        ).pack(pady=(0, 5))
        
        self.file_count = ctk.StringVar(value="1")
        self.file_dropdown = ctk.CTkOptionMenu(
            master=dropdown_frame,
            values=["1", "2", "3", "4", "5"],
            variable=self.file_count,
            command=self.update_upload_buttons,
            width=120,
            fg_color=self.colors['secondary'],
            button_color=self.colors['accent'],
            button_hover_color=self.colors['primary'],
            corner_radius=10
        )
        self.file_dropdown.pack()

        # Main upload container
        self.upload_container = ctk.CTkFrame(
            master=self.main_container, 
            fg_color="transparent"
        )
        self.upload_container.pack(padx=(20,20), pady=(20, 20), expand=True, fill="both")

        # Initial creation of upload buttons
        self.update_upload_buttons()

        # Start Automation Button
        button_frame = ctk.CTkFrame(master=self.main_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 20))
        
        self.start_button = ctk.CTkButton(
            master=button_frame,
            text="Start Automation",
            fg_color=self.colors['success'],
            hover_color="#2D8A6C",
            font=("Arial Bold", 16 ),
            text_color=self.colors['text'],
            command=self.start_automation,
            width=200,
            height=35
        )
        self.start_button.pack(pady=(20, 10))

        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_container,
            text="",
            font=("Arial", 12),
            text_color=self.colors['secondary']
        )
        self.status_label.pack(pady=(0, 10))

        # Frame for progress bars
        self.progress_frame = ctk.CTkFrame(master=self.main_container, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 20))

    def get_chrome_driver(self):
        """Get Chrome WebDriver with optimized options"""
        options = webdriver.ChromeOptions()
        
        # Performance optimizations
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        
        # Set page load strategy for faster startup
        options.page_load_strategy = 'eager'
        
        driver = None
        error_messages = []
        
        # Disable SSL verification for webdriver manager
        os.environ['WDM_SSL_VERIFY'] = '0'
        
        # Method 1: Try WebDriver Manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            print("Successfully initialized ChromeDriver using WebDriver Manager")
            return driver
        except Exception as e1:
            error_messages.append(f"WebDriver Manager: {str(e1)}")
            print(f"WebDriver Manager failed: {str(e1)}")
            
        # Method 2: Try local driver paths
        possible_paths = [
            r"C:\webdrivers\chromedriver.exe",
            r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
            r"C:\Windows\System32\chromedriver.exe",
            r".\drivers\chromedriver.exe",
            r"chromedriver.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    driver = webdriver.Chrome(service=Service(path), options=options)
                    print(f"Successfully initialized ChromeDriver from: {path}")
                    return driver
                except Exception as e2:
                    error_messages.append(f"Local path {path}: {str(e2)}")
                    print(f"Failed to use driver at {path}: {str(e2)}")
                    continue
        
        # Method 3: Try system PATH
        try:
            driver = webdriver.Chrome(options=options)
            print("Successfully initialized ChromeDriver from system PATH")
            return driver
        except Exception as e3:
            error_messages.append(f"System PATH: {str(e3)}")
            print(f"System PATH ChromeDriver failed: {str(e3)}")
        
        raise Exception(
            "Could not initialize Chrome WebDriver. Please try one of these solutions:\n\n"
            "1. Check your internet connection and try again\n"
            "2. Download ChromeDriver manually from: https://chromedriver.chromium.org/downloads\n"
            "   - Create folder: C:\\webdrivers\\\n"
            "   - Extract chromedriver.exe to C:\\webdrivers\\chromedriver.exe\n"
            "3. Add ChromeDriver to your system PATH\n"
            "4. Make sure Google Chrome browser is installed and updated\n\n"
            f"Errors encountered: {'; '.join(error_messages)}"
        )

    def create_button(self, master, text, command, color, hover_color):
        return ctk.CTkButton(
            master=master,
            text=text,
            fg_color=color,
            hover_color=hover_color,
            font=("Arial Bold", 12),
            text_color=self.colors['text'],
            command=command,
            width=150,
            height=35
        )

    def extract_credentials_from_excel(self, file_path):
        """Extract credentials from Excel file if available - Optimized"""
        try:
            # Read only first row and specific columns for faster processing
            df = pd.read_excel(file_path, nrows=1)
            
            reg_no = None
            password = None
            
            # More efficient column checking
            if 'RegistrationNo' in df.columns:
                reg_no_value = df['RegistrationNo'].iloc[0]
                reg_no = str(reg_no_value).strip() if pd.notna(reg_no_value) else None
            
            if 'Password' in df.columns:
                password_value = df['Password'].iloc[0]
                password = str(password_value).strip() if pd.notna(password_value) else None
            
            return reg_no, password
        except Exception as e:
            logger.error(f"Error extracting credentials from Excel: {str(e)}")
            return None, None

    def fast_autofill_entry(self, entry_widget, value):
        """Optimized entry autofill method"""
        if value:
            # Use configure method for faster updates
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, value)

    def update_upload_buttons(self, *args):
        # Clear existing frames
        for widget in self.upload_container.winfo_children():
            widget.destroy()
        
        # Clear dictionaries
        self.credential_entries.clear()
        self.excel_credentials.clear()
        
        file_count = int(self.file_count.get())
        
        # Create wrapper frame
        wrapper_frame = ctk.CTkFrame(
            master=self.upload_container, 
            fg_color="transparent"
        )
        wrapper_frame.pack(expand=True, fill="both")

        # Configure grid
        cols = 3 if file_count > 2 else (2 if file_count > 1 else 1)
        rows = (file_count + cols - 1) // cols

        for i in range(file_count):
            row = i // cols
            col = i % cols

            # Create file frame
            file_frame = ctk.CTkFrame(
                master=wrapper_frame, 
                fg_color="#29104A", 
                corner_radius=15,
                width=300,
                height=400
            )
            file_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            file_frame.grid_propagate(False)

            # File label
            ctk.CTkLabel(
                master=file_frame,
                text=f"File {i+1} Configuration",
                font=("Arial Bold", 16),
                text_color=self.colors['text']
            ).pack(pady=(15, 10))

            # Status label
            cred_status_label = ctk.CTkLabel(
                master=file_frame,
                text="Upload Excel file to check for credentials",
                font=("Arial", 10),
                text_color=self.colors['warning']
            )
            cred_status_label.pack(pady=(0, 10))

            # Credentials section
            cred_frame = ctk.CTkFrame(master=file_frame, fg_color="transparent")
            cred_frame.pack(fill="x", padx=15, pady=(0, 10))

            # Registration Number
            ctk.CTkLabel(
                master=cred_frame,
                text="Registration Number:",
                font=("Arial Bold", 12),
                text_color=self.colors['text']
            ).pack(anchor="w", pady=(5, 2))
            
            reg_entry = ctk.CTkEntry(
                master=cred_frame,
                placeholder_text="From Excel file or manual entry",
                font=("Arial", 11),
                height=30,
                fg_color=self.colors['secondary'],
                border_color=self.colors['accent']
            )
            reg_entry.pack(fill="x", pady=(0, 8))

            # Password
            ctk.CTkLabel(
                master=cred_frame,
                text="Password:",
                font=("Arial Bold", 12),
                text_color=self.colors['text']
            ).pack(anchor="w", pady=(0, 2))
            
            pass_entry = ctk.CTkEntry(
                master=cred_frame,
                placeholder_text="From Excel file or manual entry",
                font=("Arial", 11),
                height=30,
                show="*",
                fg_color=self.colors['secondary'],
                border_color=self.colors['accent']
            )
            pass_entry.pack(fill="x", pady=(0, 10))

            # Store entries
            self.credential_entries[i] = {
                'reg_entry': reg_entry,
                'pass_entry': pass_entry,
                'status_label': cred_status_label
            }

            # Button container
            button_container = ctk.CTkFrame(master=file_frame, fg_color="transparent")
            button_container.pack(expand=True, fill="x", padx=15, pady=(0, 15))
            
            # Buttons
            upload_button = self.create_button(
                button_container,
                f"Upload File {i+1}",
                lambda i=i: self.upload_file(i),
                self.colors['primary'],
                self.colors['secondary']
            )
            upload_button.pack(pady=(0, 5), fill="x")

            check_button = self.create_button(
                button_container,
                f"Test Login {i+1}",
                lambda i=i: self.check_upload(i),
                self.colors['accent'],
                self.colors['secondary']
            )
            check_button.pack(pady=(0, 5), fill="x")

            close_button = self.create_button(
                button_container,
                f"Close Browser {i+1}",
                lambda i=i: self.close_browser(i),
                self.colors['danger'],
                "#E65555"
            )
            close_button.pack(pady=(0, 5), fill="x")

        # Configure grid weights
        for j in range(cols):
            wrapper_frame.grid_columnconfigure(j, weight=1)
        for j in range(rows):
            wrapper_frame.grid_rowconfigure(j, weight=1)

    def upload_file(self, index):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            self.file_paths[index] = file_path
            
            # Extract credentials with optimized method
            excel_reg_no, excel_password = self.extract_credentials_from_excel(file_path)
            
            # Store Excel credentials
            self.excel_credentials[index] = {
                'reg_no': excel_reg_no,
                'password': excel_password
            }
            
            # Batch UI updates for faster autofill
            entries = self.credential_entries[index]
            
            if excel_reg_no and excel_password:
                # Both credentials found - Fast autofill
                self.fast_autofill_entry(entries['reg_entry'], excel_reg_no)
                self.fast_autofill_entry(entries['pass_entry'], excel_password)
                
                # Update status and main label in one go
                entries['status_label'].configure(
                    text="✓ Credentials found in Excel file",
                    text_color=self.colors['success']
                )
                
                self.status_label.configure(
                    text=f"File {index+1} uploaded with credentials from Excel!",
                    text_color=self.colors['success']
                )
                
            elif excel_reg_no or excel_password:
                # Partial credentials - Fast autofill for available ones
                if excel_reg_no:
                    self.fast_autofill_entry(entries['reg_entry'], excel_reg_no)
                if excel_password:
                    self.fast_autofill_entry(entries['pass_entry'], excel_password)
                
                entries['status_label'].configure(
                    text="⚠ Partial credentials found - complete manually",
                    text_color=self.colors['warning']
                )
                
                self.status_label.configure(
                    text=f"File {index+1} uploaded - please complete missing credentials!",
                    text_color=self.colors['warning']
                )
            else:
                # No credentials
                entries['status_label'].configure(
                    text="ℹ No credentials in Excel - enter manually",
                    text_color=self.colors['accent']
                )
                
                self.status_label.configure(
                    text=f"File {index+1} uploaded - please enter credentials manually!",
                    text_color=self.colors['accent']
                )

    def get_credentials(self, index):
        """Get credentials - optimized"""
        # Check Excel credentials first
        if index in self.excel_credentials:
            excel_reg = self.excel_credentials[index].get('reg_no')
            excel_pass = self.excel_credentials[index].get('password')
            
            if excel_reg and excel_pass:
                return excel_reg, excel_pass
        
        # Fallback to UI entries
        if index not in self.credential_entries:
            return None, None
        
        reg_no = self.credential_entries[index]['reg_entry'].get().strip()
        password = self.credential_entries[index]['pass_entry'].get().strip()
        
        return reg_no if reg_no else None, password if password else None

    def check_upload(self, index):
        if index not in self.file_paths:
            self.status_label.configure(
                text=f"Please upload File {index+1} first.",
                text_color=self.colors['danger']
            )
            return
        
        reg_no, password = self.get_credentials(index)
        
        if not reg_no or not password:
            self.status_label.configure(
                text=f"Please ensure both Registration Number and Password are available for File {index+1}.",
                text_color=self.colors['danger']
            )
            return

        try:
            self.status_label.configure(
                text=f"Initializing browser for File {index+1}...",
                text_color=self.colors['warning']
            )
            self.update()
            
            driver = self.get_chrome_driver()
            self.drivers[index] = driver
            
            handler = RobustElementHandler(driver)
            self.element_handlers[index] = handler
            
            self.status_label.configure(
                text=f"Loading website for File {index+1}...",
                text_color=self.colors['warning']
            )
            self.update()
            
            driver.get("https://onlinedbtagriservice.bihar.gov.in/Licence/LicenceForm/ProductDetails")
            
            handler.wait_for_page_load()
            handler.safe_find_element((By.ID, "loginForm"))
            
            # Fast credential filling
            handler.safe_send_keys((By.ID, "RegistrationNo"), reg_no)
            handler.safe_send_keys((By.ID, "Password"), password)
            
            credential_source = "Excel file" if (index in self.excel_credentials and 
                                               self.excel_credentials[index].get('reg_no') and 
                                               self.excel_credentials[index].get('password')) else "manual input"
            
            self.status_label.configure(
                text=f"Credentials from {credential_source} filled for File {index+1}. Browser ready for testing.",
                text_color=self.colors['success']
            )
            
        except Exception as e:
            self.status_label.configure(
                text=f"Error opening browser for File {index+1}: {str(e)}",
                text_color=self.colors['danger']
            )
            # Clean up
            if index in self.drivers:
                try:
                    self.drivers[index].quit()
                except:
                    pass
                del self.drivers[index]
            if index in self.element_handlers:
                del self.element_handlers[index]

    def close_browser(self, index):
        if index in self.drivers:
            try:
                self.drivers[index].quit()
                del self.drivers[index]
                if index in self.element_handlers:
                    del self.element_handlers[index]
                self.status_label.configure(
                    text=f"Browser for File {index+1} closed.",
                    text_color=self.colors['success']
                )
            except Exception as e:
                self.status_label.configure(
                    text=f"Error closing browser for File {index+1}: {str(e)}",
                    text_color=self.colors['warning']
                )
        else:
            self.status_label.configure(
                text=f"No open browser for File {index+1}.",
                text_color=self.colors['warning']
            )

    def process_file(self, excel_file, progress_bar, reg_no, password):
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            raise ValueError(f"Error reading Excel file {excel_file}: {str(e)}")

        driver = self.get_chrome_driver()
        handler = RobustElementHandler(driver)
        
        try:
            driver.get("https://onlinedbtagriservice.bihar.gov.in/Licence/LicenceForm/ProductDetails")
            handler.wait_for_page_load()

            # Login process
            handler.safe_find_element((By.ID, "loginForm"))
            handler.safe_send_keys((By.ID, "RegistrationNo"), reg_no)
            handler.safe_send_keys((By.ID, "Password"), password)

            # Click login
            login_button_locator = (By.CSS_SELECTOR, "#loginForm > form > button:nth-child(4)")
            handler.safe_click(login_button_locator)

            # Wait for form
            handler.wait_for_page_load()
            handler.safe_find_element((By.ID, 'ProductCIBCode'), timeout=45)

            # Field mappings
            field_mappings = {
                'ProductCIBCode': 'ProductCIBCode',
                'ProductRegDate': 'ProductRegDate', 
                'ProductImpterManurName': 'ManufacturerName',
                'PrincipleCertNo': 'PrincipalCerificateNo',
                'PrincipleCertValidUpto': 'PrincipleCertificateValidUpto',
                'PrincipleCertIssueDate': 'PrincipleCertificateIssueDate',
                'ProductValidityDate': 'InsecticideRegistrationValidUpto',
                'ProductName': 'ProductName'
            }

            # Validate columns
            for excel_col in field_mappings.values():
                if excel_col not in df.columns:
                    raise ValueError(f"Required column '{excel_col}' not found in Excel file")

            add_button_locator = (By.CSS_SELECTOR, "div.col-sm-8 button.btn.btn-primary.btn-block")
            total_rows = len(df)
            
            for index, row in df.iterrows():
                try:
                    # Fill fields faster with reduced timeout
                    for web_field, excel_field in field_mappings.items():
                        field_value = str(row[excel_field]) if pd.notna(row[excel_field]) else ""
                        if field_value:
                            handler.safe_send_keys((By.ID, web_field), field_value, timeout=5)
                    
                    # Click add button
                    handler.safe_click(add_button_locator, timeout=10)
                    
                    # Reduced delay for faster processing
                    time.sleep(0.3)
                    
                    # Update progress
                    progress = (index + 1) / total_rows
                    progress_bar.set(progress)
                    
                except Exception as row_error:
                    logger.error(f"Error processing row {index}: {str(row_error)}")
                    continue

        except Exception as e:
            logger.error(f"Error in process_file: {str(e)}")
            raise e
        finally:
            driver.quit()

    def start_automation(self):
        if not self.file_paths:
            self.status_label.configure(
                text="Please upload Excel files.",
                text_color=self.colors['danger']
            )
            return

        # Validate credentials
        missing_credentials = []
        for i in self.file_paths.keys():
            reg_no, password = self.get_credentials(i)
            if not reg_no or not password:
                missing_credentials.append(str(i+1))
        
        if missing_credentials:
            self.status_label.configure(
                text=f"Please complete credentials for File(s): {', '.join(missing_credentials)}",
                text_color=self.colors['danger']
            )
            return

        self.status_label.configure(
            text="Automation in progress...",
            text_color=self.colors['warning']
        )
        self.update()

        # Clear progress bars
        for widget in self.progress_frame.winfo_children():
            widget.destroy()

        # Create progress bars
        progress_bars = {}
        for i, file_path in self.file_paths.items():
            file_name = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
            progress_container = ctk.CTkFrame(master=self.progress_frame, fg_color="transparent")
            progress_container.pack(fill="x", pady=(5, 10))
            
            label = ctk.CTkLabel(
                master=progress_container,
                text=f"File {i+1}: {file_name}",
                font=("Arial", 11)
            )
            label.pack(anchor="center", pady=(0, 5))
            
            progress_bar = ctk.CTkProgressBar(
                master=progress_container,
                width=200,
                height=10,
                fg_color=self.colors['secondary'],
                progress_color=self.colors['success']
            )
            progress_bar.set(0)
            progress_bar.pack()
            progress_bars[i] = progress_bar

        def process_files():
            try:
                for i, excel_file in self.file_paths.items():
                    reg_no, password = self.get_credentials(i)
                    
                    credential_source = "Excel file" if (i in self.excel_credentials and 
                                                       self.excel_credentials[i].get('reg_no') and 
                                                       self.excel_credentials[i].get('password')) else "manual input"
                    
                    self.status_label.configure(
                        text=f"Processing file {i+1} of {len(self.file_paths)} (using {credential_source})...",
                        text_color=self.colors['warning']
                    )
                    self.update()
                    
                    try:
                        self.process_file(excel_file, progress_bars[i], reg_no, password)
                        self.status_label.configure(
                            text=f"File {i+1} processed successfully!",
                            text_color=self.colors['success']
                        )
                    except Exception as file_error:
                        self.status_label.configure(
                            text=f"Error processing file {i+1}: {str(file_error)}",
                            text_color=self.colors['danger']
                        )
                        logger.error(f"File {i+1} processing failed: {str(file_error)}")
                        continue
                    
                    self.update()

                self.status_label.configure(
                    text="All files processing completed!",
                    text_color=self.colors['success']
                )
            except Exception as e:
                self.status_label.configure(
                    text=f"An error occurred: {str(e)}",
                    text_color=self.colors['danger']
                )

        threading.Thread(target=process_files, daemon=True).start()

    def __del__(self):
        """Clean up all open drivers when the app is closed"""
        for driver in self.drivers.values():
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
