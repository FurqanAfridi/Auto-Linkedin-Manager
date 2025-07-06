
import argparse
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
import time
import os
from seleniumbase import SB
from cutie import select
from configparser import RawConfigParser
import openai
import logging
import pandas as pd
import google.generativeai as genai


TEMP_PROFILE = os.path.expanduser("~/AppData/Local/Temp/LinkedinProfile")

_CONFIG_FILENAME = "config"
_config = RawConfigParser()


# Set working directory to script location
import sys
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


logging.basicConfig(filename="Monitoring.log", filemode="w",
                    format="| %(name)s <==> %(levelname)s | %(asctime)s ==> %(message)s")
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)


# --- Refactored GPTManager class ---

class GPTManager:

    def __init__(self, config, config_filename, logger):
        """
        Initialize the GPTManager with config, config filename, and logger.
        Args:
            config: RawConfigParser object for configuration.
            config_filename: Path to the config file.
            logger: Logger object for logging errors/info.
        """
        self._config = config
        self._CONFIG_FILENAME = config_filename
        self.LOGGER = logger

    def generate_comment_for_description(self, description: str) -> str:
        """
        Generate a comment for a single post description using the current static prompt and model.
        Args:
            description: The post description or topic string.
        Returns:
            The generated comment as a string, or an error message if failed.
        """
        try:
            import openai
            openai.api_key = self._config["ALL"]["api"]
            complete_prompt = f"{self._config['ALL']['static prompt']}\n{description}\n"
            # openai>=1.0.0: use openai.chat.completions.create
            response = openai.chat.completions.create(
                model=self._config["ALL"]["ai model"],
                messages=[{"role": "user", "content": complete_prompt}]
            )
            # The new API returns response.choices[0].message.content
            return response.choices[0].message.content
        except Exception as e:
            self.LOGGER.exception("Exception while generating single comment!")
            return f"Error: {str(e)}"
            
    def openai_request(self, row: pd.Series, total: int, new_dataframe: pd.DataFrame, file_chosen: str):
        """
        Send a prompt to OpenAI and save the response to the dataframe.
        Args:
            row: Row from the input DataFrame.
            total: Total number of rows.            pip install seleniumbase
            new_dataframe: DataFrame to store generated posts.
            file_chosen: Name of the file being processed.
        """
        try:
            print(f"{row.name + 1} / {total} => Generating Comment!")
            complete_prompt = f"{self._config['ALL']['static prompt']}\n{row['Topics']}\n"
            openai.api_key = self._config["ALL"]["api"]
            response = openai.ChatCompletion.create(
                model=self._config["ALL"]["ai model"],
                messages=[
                    {"role": "user", "content": complete_prompt}
                ]
            )
            print(f"{row.name + 1} / {total} => Post generated!")
            new_dataframe.loc[len(new_dataframe)] = {"Post Data": response.choices[0].message.content}
            new_dataframe.to_excel(f"Output {file_chosen}", index=False)
            print(f"{row.name + 1} / {total} => Post saved in excel!")
        except Exception as e:
            self.LOGGER.exception("Exception while generating description!")
            print(f"{row.name + 1} / {total} => Error occurred while generating description!")

    def generate_description(self):
        """
        Generate posts in bulk from an Excel file using OpenAI and save the results.
        """
        accepted_extensions = [".xlsx"]
        files = [file for file in os.listdir("files") if os.path.splitext(file)[1] in accepted_extensions]
        os.system("cls")
        print("Choose file:")
        if not files:
            print("No Excel files found in 'files' directory.")
            input("Press Enter to continue!")
            return
        file_chosen = files[select(files)]
        dataframe = pd.read_excel(f"files/{file_chosen}", index_col=False)
        dataframe.fillna('', inplace=True)
        new_dataframe = pd.DataFrame(columns=["Post Data"])
        dataframe.apply(lambda row: self.openai_request(row, len(dataframe), new_dataframe, file_chosen), axis=1)
        input("Posts generated!\nPress Enter to continue!")

    def multiple_line_input(self, default_message: str) -> str:
        """
        Accept multi-line input from the user until an empty line is entered.
        Args:
            default_message: The message to display for the first input.
        Returns:
            The concatenated string of all input lines.
        """
        all_input = ""
        while True:
            current_input = input("> " if all_input else default_message)
            if not current_input:
                break
            all_input += current_input + " "
        return all_input

    def change_static_prompt(self):
        """
        Change the static prompt used for GPT by selecting a .txt file from the Prompts directory.
        """
        accepted_extensions = [".txt"]
        prompts = [prompt for prompt in os.listdir("Prompts") if os.path.splitext(prompt)[1] in accepted_extensions]
        os.system("cls")
        print("Choose prompt:")
        if not prompts:
            print("No prompt files found in 'Prompts' directory.")
            input("Press Enter to continue!")
            return
        prompt_chosen = prompts[select(prompts)]
        with open(f"Prompts/{prompt_chosen}", "r", encoding="utf-8") as txt_f:
            pdata = txt_f.read()
        print(pdata)
        self._config["ALL"]["static prompt"] = pdata

    def change_ai_model(self):
        """
        Change the AI model used for GPT by selecting from supported models.
        Note: openai>=1.0.0 does not support listing models with openai.Model.list().
        We'll show a static list of supported models for user selection.
        """
        models_supported = [
            'gpt-4', 'gpt-4-0613', 'gpt-4-32k', 'gpt-4-32k-0613',
            'gpt-3.5-turbo', 'gpt-3.5-turbo-0613', 'gpt-3.5-turbo-16k', 'gpt-3.5-turbo-16k-0613'
        ]
        os.system("cls")
        print("Choose AI Model:")
        model_choice = select(models_supported)
        self._config["ALL"]["ai model"] = models_supported[model_choice]

    def change_api_key(self):
        """
        Change the OpenAI API key in the configuration.
        """
        self._config["ALL"]["api"] = input("Enter API Key: ")

    def save_config(self):
        """
        Save the current configuration to the config file.
        """
        with open(self._CONFIG_FILENAME, "w", encoding="utf-8") as file:
            self._config.write(file)

    def view_config(self):
        """
        Display the current GPT-related configuration settings.
        """
        for key, val in self._config["ALL"].items():
            print(f"{key.upper()}: {val}")
        input("Press Enter to continue!")

    def change_config(self, func):
        """
        Helper to change a config value and save the config after the change.
        Args:
            func: The function that changes a config value.
        """
        func()
        self.save_config()

    def generate_config(self):
        """
        Generate a new configuration by prompting the user for all required GPT settings.
        """
        self._config.add_section("ALL")
        self.change_static_prompt()
        self.change_api_key()
        self.change_ai_model()
        self.save_config()

    def gpt_settings_menu(self):
        """
        Display the GPT settings menu and handle user choices for GPT-related actions.
        """
        while True:
            options = [
                "Generate Posts via Excel File",
                "Change Static ChatGPT Prompt",
                "Change AI Model",
                "Change OPENAI API",
                "View Settings",
                "Back to Main Menu"
            ]
            print("\n--- GPT Settings ---")
            choice = select(options)
            if choice == 0:
                self.generate_description()
            elif choice == 1:
                self.change_config(self.change_static_prompt)
            elif choice == 2:
                self.change_config(self.change_ai_model)
            elif choice == 3:
                self.change_config(self.change_api_key)
            elif choice == 4:
                self.view_config()
            elif choice == 5:
                break

# --- Refactored LinkedInManager class ---

class LinkedInManager:

    def __init__(self, gpt_manager: GPTManager, google_manager=None, config=None, mode="headon"):
        """
        Initialize the LinkedInManager with references to the GPTManager and GoogleManager for comment generation.
        mode: 'headless' (no browser UI) or 'headon' (browser UI shown)
        """
        self.driver: Chrome = None
        self.wait: WebDriverWait = None
        self.email: str = ''
        self.password: str = ''
        self.sb_init: SB = None
        self.gpt_manager = gpt_manager
        self.google_manager = google_manager
        self._config = config
        self._mode = mode
        # Default to GPT if not set
        if self._config is not None:
            if not self._config.has_section("LINKEDIN"):
                self._config.add_section("LINKEDIN")
            if not self._config["LINKEDIN"].get("comment_source"):
                self._config["LINKEDIN"]["comment_source"] = "gpt"
        # Do not start Chrome on init; start only when needed

    def start_chrome(self) -> None:
        """Start the Chrome browser for automation, using the selected mode."""
        headless = self._mode == "headless"
        self.sb_init = SB(uc=True, headed=not headless, headless2=headless, user_data_dir=TEMP_PROFILE)
        sb = self.sb_init.__enter__()
        self.driver = sb.driver
        self.wait = WebDriverWait(self.driver, 30)

    def linkedin_signin(self) -> bool:
        """Sign in to LinkedIn. Starts Chrome if not already started."""
        if self.driver is None:
            self.start_chrome()
        signin_successful = False
        self.driver.get("https://www.linkedin.com/")
        while True:
            try:
                self.driver.find_element(By.CSS_SELECTOR, "a[href*='linkedin.com/events']")
                signin_successful = True
                return signin_successful
            except:
                pass
            try:
                self.driver.find_element(By.CSS_SELECTOR, "#session_key")
                break
            except:
                pass
        self.email = input("Enter your Email: ")
        self.password = input("Enter your Password: ")
        email_input = self.wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#session_key")))
        email_input.send_keys(self.email)
        pass_inp = self.wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#session_password")))
        pass_inp.send_keys(self.password)
        signin_button = self.wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "button.btn-primary")))
        signin_button.click()
        for _ in range(10):
            try:
                self.wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='linkedin.com/events']")))
                signin_successful = True
                break
            except:
                pass
        return signin_successful

    def send_connection_requests_from_excel(self, input_excel: str, message_template: str = "Hi {Name}, I'd like to connect with you on LinkedIn!"):

        """
        Read an Excel file with a 'Profile Link' column and send connection requests with a personalized message to each user.
        """
        import pandas as pd
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import traceback

        if self.driver is None:
            self.start_chrome()

        try:
            df = pd.read_excel(input_excel)
        except Exception as e:
            print(f"Failed to read Excel file: {e}")
            return

        if 'Profile Link' not in df.columns:
            print("Excel file must contain a 'Profile Link' column.")
            return

        for idx, row in df.iterrows():
            profile_url = row.get('Profile Link', '').strip()
            name = row.get('Name', '').strip() if 'Name' in row else ''
            if not profile_url:
                print(f"Row {idx+1}: No profile link, skipping.")
                continue
            print(f"[{idx+1}/{len(df)}] Visiting: {profile_url}")
            try:
                self.driver.get(profile_url)
                time.sleep(5)
                # Try to find the Connect button
                connect_btn = None
                try:
                    # Try primary connect button
                    connect_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Connect') and not(@disabled)]"))
                    )
                except Exception:
                    # Try in the overflow menu (More...)
                    try:
                        more_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'More')]" )
                        more_btn.click()
                        time.sleep(1)
                        connect_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//span[text()='Connect']/ancestor::button[not(@disabled)]"))
                        )
                    except Exception:
                        print(f"Row {idx+1}: Could not find Connect button, skipping.")
                        continue
                connect_btn.click()
                time.sleep(2)
                # Add a note
                try:
                    add_note_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add a note')]"))
                    )
                    add_note_btn.click()
                    time.sleep(1)
                    # Fill the message
                    msg_box = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='message']"))
                    )
                    personalized_msg = message_template.format(Name=name or "there")
                    msg_box.clear()
                    msg_box.send_keys(personalized_msg)
                    time.sleep(1)
                    # Send the invitation
                    send_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Send')]" )
                    send_btn.click()
                    print(f"Row {idx+1}: Connection request sent.")
                except Exception:
                    print(f"Row {idx+1}: Could not add note or send request. Skipping.")
                    continue
                time.sleep(2)
            except Exception as e:
                print(f"Row {idx+1}: Error: {e}")
                traceback.print_exc()
                continue
        print("All connection requests processed.")

    def connection_request_menu(self):
        """
        Menu for sending connection requests from Excel.
        """
        while True:
            print("\n--- LinkedIn Connection Request Sender ---")
            options = ["Send Connection Requests from Excel", "Back to LinkedIn Menu"]
            choice = select(options)
            if choice == 0:
                input_excel = input("Enter Excel filename (default: linkedin_connections.xlsx): ").strip()
                if not input_excel:
                    input_excel = "linkedin_connections.xlsx"
                msg_template = input("Enter message template (use {Name} for personalization, default: 'Hi {Name}, I'd like to connect with you on LinkedIn!'): ").strip()
                if not msg_template:
                    msg_template = "Hi {Name}, I’m connecting with founders and operators exploring how automation and systems-thinking are shaping modern teams. Thought it’d be great to connect and share perspectives."
                self.send_connection_requests_from_excel(input_excel, msg_template)
                input("Press Enter to continue!")
            elif choice == 1:
                break
    
    def connection_hunting(self, search_url: str, output_excel: str = "linkedin_connections.xlsx"):
        """
        On a given LinkedIn search URL, grab all visible profiles and save Name, Headline, Location, and Current Position to an Excel file.
        Handles missing elements gracefully. Also paginates through all result pages.
        """
        import pandas as pd
        from selenium.webdriver.common.by import By
        import time
        import re
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        if self.driver is None:
            self.start_chrome()

        # Go to the first page
        self.driver.get(search_url)
        time.sleep(5)

        # Find total number of pages from pagination by detecting the last number button robustly
        try:
            # Wait for pagination to appear (up to 10s)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.artdeco-pagination__indicator'))
            )
            # Get all pagination buttons (including ellipsis, next, prev, etc.)
            page_btns = self.driver.find_elements(By.CSS_SELECTOR, '.artdeco-pagination__indicator')
            print(f"Found {len(page_btns)} pagination buttons (all types).")
            # Filter only those with a numeric text (ignore ellipsis, next, prev)
            numeric_btns = []
            for btn in page_btns:
                try:
                    text = btn.text.strip()
                    if text.isdigit():
                        numeric_btns.append(btn)
                except Exception:
                    continue
            print(f"Found {len(numeric_btns)} numeric pagination buttons.")
            if numeric_btns:
                last_btn = numeric_btns[-1]
                last_text = last_btn.text.strip()
                print(f"Last numeric pagination button text: '{last_text}'")
                total_pages = int(last_text)
            else:
                print("No numeric pagination buttons found, defaulting to 1 page.")
                total_pages = 1
        except Exception as e:
            print(f"Pagination detection failed: {e}. Defaulting to 1 page.")
            total_pages = 1

        # Build base_url for pagination (remove any existing page param)
        page_match = re.search(r'([?&])page=\d+', search_url)
        if page_match:
            # Remove the page param and any trailing '&' or '?' if left empty
            base_url = re.sub(r'([?&])page=\d+', '', search_url)
            # Remove trailing '?' or '&' if present
            base_url = re.sub(r'[?&]$', '', base_url)
        else:
            base_url = search_url
        # Decide how to append the page param
        if '?' in base_url:
            base_url = base_url + '&page={}'
        else:
            base_url = base_url + '?page={}'

        profiles = []
        # Try to load existing data if file exists (for resume support)
        import os
        if os.path.exists(output_excel):
            try:
                profiles = pd.read_excel(output_excel).to_dict(orient='records')
            except Exception:
                profiles = []

        pagest = input(f"Enter the page number to start from (1-{total_pages}, default 1): ").strip()
        if pagest.isdigit() and 1 <= int(pagest) <= total_pages:
            start_page = int(pagest)
        for page in range(start_page, total_pages + 1):
            url = base_url.format(page)
            print(f"Processing page {page} of {total_pages}")
            self.driver.get(url)
            time.sleep(5)
            # Scroll to load all profiles on the page
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 5
            while scroll_attempts < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1

            # Find all profile containers (robust selector for LinkedIn search results)
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.EWKNtlaOOYwGboxrLECAryApIuqhVXpZuIFdE')
            for card in cards:
                # Name and Profile Link
                try:
                    a_elem = card.find_element(By.CSS_SELECTOR, 'a[href*="/in/"]')
                    name_elem = a_elem.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]')
                    name = name_elem.text.strip()
                    profile_link = a_elem.get_attribute('href')
                except Exception:
                    name = ""
                    profile_link = ""
                # Headline (role/title)
                try:
                    headline_elem = card.find_element(By.CSS_SELECTOR, 'div.t-14.t-black.t-normal')
                    headline = headline_elem.text.strip()
                except Exception:
                    headline = ""
                # Location (try to get the second t-14.t-normal div if available)
                try:
                    location_elem = None
                    divs = card.find_elements(By.CSS_SELECTOR, 'div.t-14.t-normal')
                    if len(divs) > 1:
                        location_elem = divs[1]
                    elif len(divs) == 1:
                        location_elem = divs[0]
                    if location_elem:
                        location = location_elem.text.strip()
                    else:
                        location = ""
                except Exception:
                    location = ""
                # Current Position (from summary paragraph, if present)
                try:
                    current_position_elem = card.find_element(By.CSS_SELECTOR, 'p.entity-result__summary--2-lines')
                    # Remove label 'Current:' and get the rest
                    current_position = current_position_elem.text.replace('Current:', '').strip()
                except Exception:
                    current_position = ""
                profiles.append({
                    "Name": name,
                    "Profile Link": profile_link,
                    "Headline": headline,
                    "Location": location,
                    "Current Position": current_position
                })

            # Save after each page to avoid data loss
            try:
                df = pd.DataFrame(profiles)
                df.to_excel(output_excel, index=False)
                print(f"Saved {len(df)} profiles to {output_excel} (up to page {page})")
            except Exception as e:
                print(f"Error saving data after page {page}: {e}")

        print(f"Saved {len(profiles)} profiles to {output_excel}")

    def connection_hunting_menu(self):
        """
        Menu for LinkedIn connection hunting feature.
        """
        while True:
            print("\n--- LinkedIn Connection Hunting ---")
            options = ["Start Connection Hunting", "Back to LinkedIn Menu"]
            choice = select(options)
            if choice == 0:
                search_url = input("Enter LinkedIn search URL: ").strip()
                output_excel = input("Enter output Excel filename (default: linkedin_connections.xlsx): ").strip()
                if not output_excel:
                    output_excel = "linkedin_connections.xlsx"
                self.connection_hunting(search_url, output_excel)
                input("Press Enter to continue!")
            elif choice == 1:
                break

    def _like_and_comment_on_posts(self, posts, processed_posts=None, max_posts=10, require_long_content=False):
        """
        Like and comment on LinkedIn posts. Used by both monitor_feed and warmup_profile_activity.
        - posts: list of Selenium WebElement posts
        - processed_posts: set of post IDs to avoid duplicates (optional)
        - max_posts: maximum number of posts to process
        - require_long_content: if True, only comment if content >= 100 chars (for feed); else always comment (for warmup)
        Returns: number of posts processed
        """
        count = 0
        for idx, post in enumerate(posts):
            if count >= max_posts:
                break
            try:
                # Unique post id logic (optional for warmup)
                post_id = None
                if processed_posts is not None:
                    try:
                        post_id = post.get_attribute('data-urn') or post.get_attribute('data-id') or f'post-{idx}'
                    except Exception:
                        post_id = f'post-{idx}'
                    if post_id in processed_posts:
                        continue

                # Extract post description
                try:
                    content_elem = post.find_element(By.CSS_SELECTOR, 'div.update-components-text.relative.update-components-update-v2__commentary span.break-words span[dir="ltr"]')
                    content = content_elem.text.strip()
                except Exception:
                    content = "[Could not extract post text]"

                # Scroll post into view
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post)
                    time.sleep(2)
                except Exception:
                    pass

                # Like the post
                liked = False
                try:
                    like_buttons = post.find_elements(By.CSS_SELECTOR, 'button.react-button__trigger[aria-label*="Like"]')
                    like_button = None
                    for btn in like_buttons:
                        if 'follow' not in btn.get_attribute('class').lower() and 'Follow' not in btn.get_attribute('aria-label'):
                            like_button = btn
                            break
                    if like_button:
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", like_button)
                        time.sleep(2)
                        aria_pressed = like_button.get_attribute('aria-pressed')
                        if aria_pressed is None or aria_pressed == 'false':
                            like_button.click()
                            print(f"Post {idx+1}: Liked!")
                            liked = True
                        else:
                            print(f"Post {idx+1}: Already liked.")
                            liked = True
                    else:
                        print(f"Post {idx+1}: Like button not found.")
                except Exception:
                    print(f"Post {idx+1}: Could not click like button.")
                time.sleep(2)

                # Comment if liked
                do_comment = liked
                if require_long_content:
                    do_comment = liked and content and len(content) >= 100
                if do_comment:
                    try:
                        comment_buttons = post.find_elements(By.CSS_SELECTOR, 'button[id^="feed-shared-social-action-bar-comment-"]')
                        if comment_buttons:
                            comment_button = comment_buttons[0]
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comment_button)
                            time.sleep(2)
                            comment_button.click()
                            time.sleep(2)
                            comment_input = post.find_element(By.CSS_SELECTOR, 'div.editor-content.ql-container div.ql-editor[contenteditable="true"]')
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", comment_input)
                            time.sleep(2)
                            comment_input.click()
                            # Generate a comment using the selected manager and insert it
                            try:
                                comment_source = "gpt"
                                if self._config is not None and self._config.has_section("LINKEDIN"):
                                    comment_source = self._config["LINKEDIN"].get("comment_source", "gpt")
                                if comment_source == "google" and self.google_manager is not None:
                                    generated_comment = self.google_manager.generate_comment_for_description(content)
                                else:
                                    generated_comment = self.gpt_manager.generate_comment_for_description(content)
                                time.sleep(2)
                                print(f"Generated Comment: {generated_comment}")
                                comment_input.send_keys(generated_comment)
                                time.sleep(2)
                                # Find and click the submit/post button
                                submit_btn = None
                                try:
                                    submit_btn = post.find_element(By.CSS_SELECTOR, 'button.comments-comment-box__submit-button--cr')
                                except Exception:
                                    pass
                                if not submit_btn:
                                    try:
                                        submit_btn = post.find_element(By.CSS_SELECTOR, 'button.comments-comment-box__submit-button, button[aria-label="Post comment"], button[aria-label="Post"]')
                                    except Exception:
                                        pass
                                if submit_btn:
                                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_btn)
                                    time.sleep(2)
                                    submit_btn.click()
                                    print(f"Post {idx+1}: Comment posted!")
                                else:
                                    print(f"Post {idx+1}: Could not find post/submit button.")
                            except Exception as e:
                                print(f"Post {idx+1}: Error generating or inserting comment: {e}")
                        else:
                            print(f"Post {idx+1}: Comment button not found.")
                    except Exception as e:
                        print(f"Post {idx+1}: Could not open comment box or insert comment. Error: {e}")
                    time.sleep(2)
                if processed_posts is not None and post_id is not None:
                    processed_posts.add(post_id)
                count += 1
            except Exception as e:
                print(f"Error processing post {idx+1}: {e}")
        return count

    def monitor_feed(self, refresh_interval: int = 60):
        """
        Monitor the LinkedIn feed, process only new posts (not previously processed):
        - For each new post: like, comment, and wait 5 seconds between actions to humanize.
        - After processing, wait for the refresh interval, then refresh and process only new posts.
        """
        print("Starting LinkedIn Manager for Feed Monitoring and Interaction ...")
        self.driver.get("https://www.linkedin.com/feed/")
        processed_posts = set()  # Track post unique ids to avoid duplicate actions
        first_run = True
        while True:
            try:
                print("\nRefreshing feed...")
                if not first_run:
                    self.driver.refresh()
                else:
                    first_run = False
                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(15)  # Wait for feed to load
                posts = self.driver.find_elements(By.CSS_SELECTOR, 'div.feed-shared-update-v2, div.feed-shared-update')
                print(f"Found {len(posts)} posts on the feed.")
                new_posts_processed = self._like_and_comment_on_posts(posts, processed_posts, max_posts=10, require_long_content=True)
                print(f"Processed {new_posts_processed} new posts, waiting for next refresh...")
                print(f"Waiting {refresh_interval} seconds before next refresh...")
                time.sleep(refresh_interval)
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"Error during monitoring: {e}")
                time.sleep(refresh_interval)

    def warmup_profile_activity(self, input_excel: str):
        """
        Visit a LinkedIn profile's activity page, like and comment on the latest 10 posts.
        Comments are generated using Gemini (Google) AI, with the same prompt as the feed monitoring function.
        """
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if self.driver is None:
            self.start_chrome()

        try:
            df = pd.read_excel(input_excel)
        except Exception as e:
            print(f"Failed to read Excel file: {e}")
            return

        if 'Profile Link' not in df.columns:
            print("Excel file must contain a 'Profile Link' column.")
            return

        for idx, row in df.iterrows():
            profile_url = row.get('Profile Link', '').strip()
            name = row.get('Name', '').strip() if 'Name' in row else ''
            if '?' in profile_url:
                profile_url = profile_url.split('?', 1)[0]
            profile_url = profile_url.rstrip('/')
            activity_url = profile_url + '/recent-activity/all/'
            print(f"Visiting activity page: {activity_url}")
            self.driver.get(activity_url)
            time.sleep(3)
            print(f"[{idx+1}/{len(df)}] Visiting: {profile_url}")
            self.driver.get(activity_url)
            time.sleep(5)
            # Scroll to load posts
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            posts = self.driver.find_elements(By.CSS_SELECTOR, 'div.feed-shared-update-v2, div.feed-shared-update')
            print(f"Found {len(posts)} posts on activity page.")
            count = self._like_and_comment_on_posts(posts, processed_posts=None, max_posts=10, require_long_content=False)
            print(f"Warmed up {count} posts on {profile_url}")

    def warmup_profile_menu(self):
        """
        Menu for warming up LinkedIn profiles from Excel (like & comment on latest 10 posts).
        """
        while True:
            print("\n--- LinkedIn Profile Warmup ---")
            options = ["Warmup Profile Activity from Excel", "Back to LinkedIn Menu"]
            choice = select(options)
            if choice == 0:
                input_excel = input("Enter Excel filename with LinkedIn profile URLs (default: linkedin_connections.xlsx): ").strip()
                if not input_excel:
                    input_excel = "linkedin_connections.xlsx"
                self.warmup_profile_activity(input_excel)
                input("Press Enter to continue!")
            elif choice == 1:
                break
    
    def linkedin_settings(self):
        """
        LinkedIn settings menu: choose comment generation source (GPT or Gemini/Google).
        """
        while True:
            options = [
                "Choose Comment Generation Source (GPT or Gemini)",
                "View Current Source",
                "Back to LinkedIn Menu"
            ]
            print("\n--- LinkedIn Settings ---")
            choice = select(options)
            if choice == 0:
                sources = ["gpt", "google"]
                print("Choose comment generation source:")
                src_choice = select(["OpenAI GPT", "Google Gemini"])
                if not self._config.has_section("LINKEDIN"):
                    self._config.add_section("LINKEDIN")
                self._config["LINKEDIN"]["comment_source"] = sources[src_choice]
                # Save config (handle config file name robustly)
                config_filename = getattr(self._config, '_CONFIG_FILENAME', None)
                if not config_filename:
                    # Try to use the global _CONFIG_FILENAME if available
                    try:
                        from __main__ import _CONFIG_FILENAME as global_config_filename
                        config_filename = global_config_filename
                    except Exception:
                        config_filename = "config"
                with open(config_filename, "w", encoding="utf-8") as file:
                    self._config.write(file)
                print(f"Comment generation source set to: {sources[src_choice]}")
            elif choice == 1:
                src = self._config["LINKEDIN"].get("comment_source", "gpt")
                print(f"Current comment generation source: {src}")
                input("Press Enter to continue!")
            elif choice == 2:
                break

    def kill_browser(self):
        self.driver.quit()
        self.sb_init.__exit__(None, None, None)


# --- GoogleManager class for Gemini integration and settings ---
class GoogleManager:
    def __init__(self, config, config_filename, logger):
        """
        Initialize the GoogleManager with config, config filename, and logger.
        Args:
            config: RawConfigParser object for configuration.
            config_filename: Path to the config file.
            logger: Logger object for logging errors/info.
        """
        self._config = config
        self._CONFIG_FILENAME = config_filename
        self.LOGGER = logger
        self._ensure_config_keys()
        self._configure_gemini()

    def _ensure_config_keys(self):
        if not self._config.has_section("GOOGLE"):
            self._config.add_section("GOOGLE")
        if not self._config["GOOGLE"].get("api"):
            self._config["GOOGLE"]["api"] = ""
        if not self._config["GOOGLE"].get("static prompt"):
            self._config["GOOGLE"]["static prompt"] = "Write a short, positive comment for this LinkedIn post:"
        self.save_config()

    def _configure_gemini(self):
        api_key = self._config["GOOGLE"].get("api", "")
        if api_key:
            genai.configure(api_key=api_key)
            try:
                models = genai.list_models()
                #print("\nAvailable Gemini models (not deprecated, showing up to 5):")
                available_models = []
                display_names = []
                # Filter and sort models: prefer 'gemini-1.5' and 'flash' in name, then by name descending
                filtered = [m for m in models if not (hasattr(m, 'description') and m.description and 'deprecated' in m.description.lower())]
                # Only include models that support 'generateContent'
                filtered = [m for m in filtered if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods]
                # Sort: prefer 'gemini-1.5' and 'flash', then by name descending
                filtered.sort(key=lambda m: (not (('gemini-1.5' in m.name) or ('flash' in m.name)), m.name), reverse=True)
                filtered = filtered[:5]
                for m in filtered:
                    available_models.append(m.name)
                    display_names.append(getattr(m, 'display_name', m.name))
                    #print(f"- {m.name} ({getattr(m, 'display_name', '')})")
                self._config["GOOGLE"]["available_models"] = ",".join(available_models)
                self._config["GOOGLE"]["available_model_names"] = ",".join(display_names)
                selected_model = self._config["GOOGLE"].get("selected_model", "")
                if selected_model and selected_model in available_models:
                    self.model = genai.GenerativeModel(selected_model.split("/")[-1])
                elif available_models:
                    self.model = genai.GenerativeModel(available_models[0].split("/")[-1])
                    self._config["GOOGLE"]["selected_model"] = available_models[0]
                else:
                    print("No non-deprecated Gemini models found that support generateContent.")
                    self.model = None
                self.save_config()
            except Exception as e:
                print(f"Error listing Gemini models: {e}")
                self.model = None
        else:
            self.model = None

    def change_gemini_model(self):
        """
        Allow the user to select a Gemini model from the latest 5 non-deprecated models.
        """
        api_key = self._config["GOOGLE"].get("api", "")
        if not api_key:
            print("Set your Gemini API key first.")
            return
        genai.configure(api_key=api_key)
        try:
            models = genai.list_models()
            filtered = [m for m in models if not (hasattr(m, 'description') and m.description and 'deprecated' in m.description.lower())]
            filtered = [m for m in filtered if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods]
            filtered.sort(key=lambda m: (not (('gemini-1.5' in m.name) or ('flash' in m.name)), m.name), reverse=True)
            filtered = filtered[:5]
            available_models = [m.name for m in filtered]
            display_names = [getattr(m, 'display_name', m.name) for m in filtered]
            if not available_models:
                print("No non-deprecated Gemini models found that support generateContent.")
                return
            print("Choose Gemini model:")
            for i, (name, disp) in enumerate(zip(available_models, display_names)):
                print(f"{i+1}. {name} ({disp})")
            idx = select([f"{name} ({disp})" for name, disp in zip(available_models, display_names)])
            self._config["GOOGLE"]["selected_model"] = available_models[idx]
            self.save_config()
            print(f"Selected Gemini model: {available_models[idx]}")
            self._configure_gemini()
        except Exception as e:
            print(f"Error listing Gemini models: {e}")

    def generate_comment_for_description(self, description: str) -> str:
        """
        Generate a comment for a post description using Gemini.
        Args:
            description: The post description or topic string.
        Returns:
            The generated comment as a string, or an error message if failed.
        """
        try:
            if not self.model:
                self._configure_gemini()
            if not self.model:
                return "Error: Gemini API key not set."
            prompt = self._config["GOOGLE"].get("static prompt", "")
            full_prompt = f"{prompt}\n{description}" if prompt else description
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            self.LOGGER.exception("Exception while generating Gemini comment!")
            return f"Error: {str(e)}"

    def change_static_prompt(self):
        """
        Change the static prompt used for Gemini by selecting a .txt file from the Prompts directory.
        """
        accepted_extensions = [".txt"]
        prompts = [prompt for prompt in os.listdir("Prompts") if os.path.splitext(prompt)[1] in accepted_extensions]
        os.system("cls")
        print("Choose prompt for Gemini:")
        if not prompts:
            print("No prompt files found in 'Prompts' directory.")
            input("Press Enter to continue!")
            return
        prompt_chosen = prompts[select(prompts)]
        with open(f"Prompts/{prompt_chosen}", "r", encoding="utf-8") as txt_f:
            pdata = txt_f.read()
        print(pdata)
        self._config["GOOGLE"]["static prompt"] = pdata
        self.save_config()

    def change_api_key(self):
        """
        Change the Gemini API key in the configuration.
        """
        self._config["GOOGLE"]["api"] = input("Enter Gemini API Key: ")
        self.save_config()
        self._configure_gemini()

    def save_config(self):
        with open(self._CONFIG_FILENAME, "w", encoding="utf-8") as file:
            self._config.write(file)

    def view_config(self):
        for key, val in self._config["GOOGLE"].items():
            print(f"{key.upper()}: {val}")
        input("Press Enter to continue!")

    def google_settings_menu(self):
        while True:
            options = [
                "Change Static Gemini Prompt",
                "Change Gemini API Key",
                "Change Gemini Model",
                "View Gemini Settings",
                "Back to Main Menu"
            ]
            print("\n--- Gemini Settings ---")
            choice = select(options)
            if choice == 0:
                self.change_static_prompt()
            elif choice == 1:
                self.change_api_key()
            elif choice == 2:
                self.change_gemini_model()
            elif choice == 3:
                self.view_config()
            elif choice == 4:
                break


# --- Main Application Workflow ---

# --- Main entrypoint: all runtime logic must be in main() and only run if __name__ == "__main__" ---
def main():
    while True:
        break
    parser = argparse.ArgumentParser(description="LinkedIn Automation Tool")
    parser.add_argument("--feed-monitoring", action="store_true", help="Run feed monitoring mode")
    parser.add_argument("--send-connections", type=str, help="Excel file for sending connection requests")
    parser.add_argument("--message", type=str, help="Message template for connection requests")
    parser.add_argument("--profile-warmup", type=str, help="Excel file for profile warmup")
    parser.add_argument("--connection-hunting", type=str, help="LinkedIn search URL for connection hunting")
    parser.add_argument("--output", type=str, help="Output Excel filename for connection hunting")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--headon", action="store_true", help="Run browser in headed (UI) mode")
    parser.add_argument("--comment-source", type=str, choices=["gpt", "google"], help="Comment generation source: gpt or google")

    parser.add_argument("--max-posts", type=int, help="Max posts to like/comment per profile/feed")
    parser.add_argument("--refresh-interval", type=int, help="Feed refresh interval in seconds")
    args = parser.parse_args()

    # Load config and managers
    # Ensure all class definitions are above this point!
    if not os.path.exists(_CONFIG_FILENAME):
        gpt_manager = GPTManager(_config, _CONFIG_FILENAME, LOGGER)
        gpt_manager.generate_config()
        google_manager = GoogleManager(_config, _CONFIG_FILENAME, LOGGER)
    else:
        _config.read(_CONFIG_FILENAME, encoding="utf-8")
        gpt_manager = GPTManager(_config, _CONFIG_FILENAME, LOGGER)
        google_manager = GoogleManager(_config, _CONFIG_FILENAME, LOGGER)

    # Determine browser mode
    if args.headless:
        linkedin_mode = "headless"
    elif args.headon:
        linkedin_mode = "headon"
    else:
        linkedin_mode = "headon"  # default

    # Set comment source if provided
    if args.comment_source:
        if not _config.has_section("LINKEDIN"):
            _config.add_section("LINKEDIN")
        _config["LINKEDIN"]["comment_source"] = args.comment_source
        with open(_CONFIG_FILENAME, "w", encoding="utf-8") as file:
            _config.write(file)

    # Set max posts if provided
    max_posts = args.max_posts if args.max_posts else 10

    # Create LinkedInManager with selected mode
    linkedin_manager = LinkedInManager(gpt_manager, google_manager=google_manager, config=_config, mode=linkedin_mode)

    # Feed Monitoring
    if args.feed_monitoring:
        if linkedin_manager.linkedin_signin():
            try:
                interval = args.refresh_interval if args.refresh_interval else 60
                linkedin_manager.monitor_feed(refresh_interval=interval)
            except Exception as e:
                print(f"Error: {e}")
            finally:
                linkedin_manager.kill_browser()
        else:
            print("Sign in failed.")
        # Do not return, allow further code to run if needed

    # Send Connection Requests
    if args.send_connections:
        if linkedin_manager.linkedin_signin():
            try:
                msg_template = args.message if args.message else "Hi {Name}, I'd like to connect with you on LinkedIn!"
                linkedin_manager.send_connection_requests_from_excel(args.send_connections, msg_template)
            except Exception as e:
                print(f"Error: {e}")
            finally:
                linkedin_manager.kill_browser()
        else:
            print("Sign in failed.")
        # Do not return, allow further code to run if needed

    # Profile Warmup
    if args.profile_warmup:
        if linkedin_manager.linkedin_signin():
            try:
                linkedin_manager.warmup_profile_activity(args.profile_warmup)
            except Exception as e:
                print(f"Error: {e}")
            finally:
                linkedin_manager.kill_browser()
        else:
            print("Sign in failed.")
        # Do not return, allow further code to run if needed

    # Connection Hunting
    if args.connection_hunting:
        if linkedin_manager.linkedin_signin():
            try:
                output_file = args.output if args.output else "linkedin_connections.xlsx"
                linkedin_manager.connection_hunting(args.connection_hunting, output_file)
            except Exception as e:
                print(f"Error: {e}")
            finally:
                linkedin_manager.kill_browser()
        else:
            print("Sign in failed.")
        # Do not return, allow further code to run if needed

    # If no CLI args, run interactive menu as before
    while True:
        main_options = ["LinkedIn Manager", "GPT Manager", "Gemini Manager", "Quit"]
        print("\n=== Main Menu ===")
        main_choice = select(main_options)
        if main_choice == 0:
            # LinkedIn Manager submenu
            while True:
                linkedin_options = ["Feed Monitoring", "LinkedIn Settings", "Connection Hunting", "Connection Request Sender", "Profile Warmup", "Back to Main Menu"]
                print("\n--- LinkedIn Manager ---")
                linkedin_choice = select(linkedin_options)
                if linkedin_choice == 0:
                    # Feed Monitoring
                    if linkedin_manager.linkedin_signin():
                        try:
                            interval = input("Enter refresh interval in seconds (default 60): ")
                            interval = int(interval) if interval.strip().isdigit() else 60
                            linkedin_manager.monitor_feed(refresh_interval=interval)
                        except Exception as e:
                            print(f"Error: {e}")
                        finally:
                            linkedin_manager.kill_browser()
                    else:
                        print("Sign in failed.")
                elif linkedin_choice == 1:
                    linkedin_manager.linkedin_settings()
                elif linkedin_choice == 2:
                    linkedin_manager.connection_hunting_menu()
                elif linkedin_choice == 3:
                    linkedin_manager.connection_request_menu()
                elif linkedin_choice == 4:
                    linkedin_manager.warmup_profile_menu()
                elif linkedin_choice == 5:
                    break
        elif main_choice == 1:
            # GPT Manager
            gpt_manager.gpt_settings_menu()
        elif main_choice == 2:
            # Gemini Manager
            google_manager.google_settings_menu()
        elif main_choice == 3:
            print("Exiting application.")
            break


if __name__ == "__main__":
    main()
