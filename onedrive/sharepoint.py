import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


__ALL__ = ["SharePoint"]


class SharePoint(object):
    dotdot = "//*[contains(@class, 'ms-Breadcrumb-listItem')]//button"
    dlbtn = "//span[contains(@class, 'ms-ContextualMenu-itemText') and contains(text(), 'Download')]"
    ddd = "//button[@data-automationid='FieldRender-DotDotDot']"
    items = "//*[@class='ms-List-cell']//*[contains(@class, 'ms-DetailsRow-cellCheck')]"
    img_types = "//*[@class='ms-List-cell']//*[contains(@class, 'ms-DetailsRow-cell')]/i/img"
    names = "//*[@class='ms-List-cell']//*[contains(@class, 'ms-DetailsRow-fields')]//*[contains(@class, 'ms-DetailsRow-cell')][2]//button[@data-automationid='FieldRenderer-name']"
    folder_name = "//*[contains(@class, 'ms-Breadcrumb-listItem')]//div[contains(@class,'ms-TooltipHost')]"
    scroll_to_bottom = '''document.querySelector(".ms-ScrollablePane div:nth-of-type(2)").scrollTo(0,99999);'''

    def __init__(self, onedrive_links: list,
                 save_dir: str,
                 chromedriver_location: str = None,
                 throttle_fallback: bool = False):
        if chromedriver_location is not None:
            chrome_options = ChromeOptions()
            chrome_prefs = {
                "download.default_directory": save_dir,
                "download.prompt_for_download": False,
                "profile.default_content_setting_values.automatic_downloads": 1
            }
            chrome_options.add_experimental_option("prefs", chrome_prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            driver = webdriver.Chrome(executable_path=chromedriver_location, options=chrome_options)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })
        driver.maximize_window()
        self.static = 5
        self.timeout = 5
        self.save_dir = save_dir
        self.throttle_fallback = throttle_fallback
        for onedrive_link in onedrive_links:
            print(onedrive_link, flush=True)
            driver.get(onedrive_link)
            self.loop_folder(driver, root=True)
        driver.quit()

    def scroll_to_bottom_4(self, d):
        for i in range(0, 4):
            d.execute_script(self.scroll_to_bottom)
            time.sleep(1)

    def mkdir(self, d):
        try:
            os.makedirs(d)
        except:
            pass

    def xpath(self, d, x):
        return WebDriverWait(d, self.timeout).until(EC.presence_of_element_located((By.XPATH, x)))

    def xpaths(self, d, x):
        return WebDriverWait(d, self.timeout).until(EC.presence_of_all_elements_located((By.XPATH, x)))

    def get_current_folder(self, d):
        e = self.xpaths(d, self.folder_name)
        txt = e[-1].text
        return txt

    def get_folder_items(self, d):
        _items = self.xpaths(d, self.items)
        _ddd = self.xpaths(d, self.ddd)
        _img_types = self.xpaths(d, self.img_types)
        return [(e.text,
                 e,
                 _items[i],
                 _ddd[i],
                 True if "sharedfolder" in _img_types[i].get_attribute("src") else False
                 ) for i, e in enumerate(self.xpaths(d, self.names))]

    def sleep(self, s: int):
        for i in range(s, -1, -1):
            time.sleep(1)
            print("\rthrottled, please wait {}:{}".format(
                str(i//60).zfill(2),
                str(i%60).zfill(2)
            ), end="", flush=True)
        print(flush=True)

    def loop_folder(self, d, location=None, root=False):
        if location is None:
            location = []
        time.sleep(self.static)
        while True:
            try:
                self.scroll_to_bottom_4(d)
                break
            except:
                self.sleep(60*5)
                d.refresh()
        while True:
            try:
                current_root_folder = self.get_current_folder(d)
                break
            except:
                self.sleep(60*5)
                d.refresh()
        if not current_root_folder:
            d.quit()
            raise Exception("empty current_root_folder")
        while True:
            try:
                folder_items = self.get_folder_items(d)
                break
            except:
                return self.return_parent(d, root, False)
        location.append(current_root_folder)
        for i in range(0, len(folder_items)):
            while True:
                try:
                    folder_items = self.get_folder_items(d)
                    break
                except:
                    return self.return_parent(d, root, False)
            current_folder = "\\".join(location)
            current_location = " > ".join(location+[folder_items[i][0]])
            if not folder_items[i][4]:
                print(current_location)
                if os.path.isfile(self.save_dir+current_folder+"\\"+folder_items[i][0]):
                    continue
                self._download(d, folder_items[i], current_folder)
            else:
                folder_items[i][1].click()
                time.sleep(self.static)
                if not self.loop_folder(d, location.copy()):
                    if not self.throttle_fallback:
                        raise Exception("onedrive throttle")
                    folder_items = self.get_folder_items(d)
                    print(current_location)
                    self._download(d, folder_items[i], current_folder)
        return self.return_parent(d, root, True)

    def return_parent(self, d, r, b):
        if not r:
            self.xpaths(d, self.dotdot)[-1].click()
        return b
    
    def _download(self, d, folder_items_i, current_folder):
        folder_items_i[2].click()
        folder_items_i[3].click()
        self.xpath(d, self.dlbtn).click()
        folder_items_i[2].click()
        time.sleep(self.static)
        crdownload = [0]
        while len(crdownload) >= 1:
            crdownload = [0 for f in os.listdir(self.save_dir) if f.endswith(".crdownload")]
        self.mkdir(self.save_dir+current_folder+"\\")
        old_fn = os.listdir(self.save_dir)[0]
        if os.path.isfile(self.save_dir+old_fn):
            if old_fn.startswith("OneDrive_") and old_fn.endswith(".zip"):
                new_fn = folder_items_i[0]+".zip"
            else:
                new_fn = old_fn
            shutil.move(self.save_dir+old_fn, self.save_dir+current_folder+"\\"+new_fn)


