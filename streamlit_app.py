import pandas as pd
import re
import streamlit as st
import streamlit_ext as ste
import time

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# parse image url to return in proper format
def format_url(src):
    # remove formatting from jepg
    if '.jepg' in src:
        url = re.split('(.jepg)', src)[:2]
        src = ''.join(url)
    # remove formatting from jpg
    if '.jpg' in src:
        url = re.split('(.jpg)', src)[:2]
        src = ''.join(url)
    # remove formatting from png
    if '.png' in src:
        url = re.split('(.png)', src)[:2]
        src = ''.join(url)
    # replace .webp with jpg
    if '.webp' in src:
        src = re.split('.webp', src)[0] + '.jpg'
    # replace .gif with jpg
    if '.gif' in src:
        src = re.split('.gif', src)[0] + '.jpg'
    return src

# cache to prevent computation on rerun
def convert_df(df):
    return df.to_csv().encode('utf-8')

# wait for element from webpage to appear before doing anything
def wait_for_loading(driver, type, value):
    try:
        return WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((type, value))
        )
    except TimeoutException:
        return False

# configure and initialize chrome driver
@st.cache_resource
def get_driver():
    # set chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox') 
    options.add_argument('--disable-gpu')
    options.add_argument('--headless')
    options.add_argument("--incognito")
    options.add_argument("--no-proxy-server")
    options.add_argument("--window-size=960,1080")
    options.add_argument("--disable-dev-shm-usage")
    #initialize Chrome Webdriver
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    return webdriver.Chrome(service=service, options=options)

# App title
st.set_page_config(page_title="Image Scraper")
st.title('📸 Image Scraper')
st.caption('This app takes a CSV, searches Google Images and appends the first image url results.')
st.markdown('---')

# Instructions
st.subheader('How to use 📖')
st.markdown("1. Paste search terms into text box below")
text_input = st.text_area('Items to search!', value=None)
st.markdown("2. Wait for scraper to complete")
st.markdown("3. Copy output")
st.markdown('---')

# Start scraper only when a CSV file is uploaded
if text_input is not None:
    st.subheader('Running scraper 🔁')
    item_list = text_input.splitlines()
    og_df = pd.DataFrame(item_list, columns=['search_term'])

    # remove duplicate rows from CSV
    df = og_df.drop_duplicates()
    search_terms = df["search_term"].values
    image_urls = []
    
    # initial url to scrape
    base_url = "https://images.google.com/"

    with st.status(f'Initializing Chrome Driver 😵‍💫', expanded=True) as status:
        # initialize chrome driver
        driver = get_driver()

        # open google images
        driver.get(base_url)

        # adjust as needed
        time.sleep(3)

        if not wait_for_loading(driver, By.CLASS_NAME, "gLFyf"):
            st.write("NOT FOUND: The search bar is not on the page.")
            exit(-1)
        driver.find_element(By.CLASS_NAME, "gLFyf").send_keys("Home")

        # Ensure the search CTA (Call To Action) is on the page
        if not wait_for_loading(driver, By.CLASS_NAME, "zgAlFc"):
            st.write("NOT FOUND: The search CTA is not on the page.")
            exit(-1)
        # Click the search button
        driver.find_element(By.CLASS_NAME, "zgAlFc").click()

    status.update(label=f"Chrome driver initialized ✅!", state="complete", expanded=False)
    
    for count, term in enumerate(search_terms):
        with st.status(f'Searching 🔁', expanded=True) as status:
            try:
                if not wait_for_loading(driver, By.CLASS_NAME, "og3lId"):
                    continue
                # clear search
                driver.find_element(By.CLASS_NAME, "og3lId").clear()
                driver.find_element(By.CLASS_NAME, "og3lId").send_keys(term)  # Write key

                # Execute the search
                if not wait_for_loading(driver, By.CLASS_NAME, "XZ5MVe"):
                    st.write("Search Button Found")
                    continue
                time.sleep(3)
                driver.find_element(By.CLASS_NAME, "XZ5MVe").click()  # Search

                # Wait for the results page to load
                if not wait_for_loading(driver, By.ID, "islrg"):
                    continue
                page = driver.find_element(By.ID, "islrg")

                # Check for at least one image in results
                if not wait_for_loading(page, By.CLASS_NAME, "islir"):
                    continue
                image_boxes = page.find_elements(By.CLASS_NAME, "islir")

                ####### CLICK INTO IMAGE FROM RESULTS
                for image_box in image_boxes:
                    # Scroll to and click the image element
                    driver.execute_script("arguments[0].scrollIntoView();", image_box)
                    image_box.click()
                    st.write("*Clicked into image* 🖱")
                    time.sleep(3)  # Adjust if necessary

                    # Check for the primary image
                    if wait_for_loading(driver, By.CLASS_NAME, "iPVvYb"):
                        src = driver.find_element(By.CLASS_NAME, "iPVvYb").get_attribute("src")
                        # ensure image url is properly formatted
                        src = format_url(src)
                        image_urls.append(src)
                        st.write(f'Valid image found: {src}')
                        break

                    # Check for the carousel image if the primary image was not found
                    elif wait_for_loading(driver, By.CLASS_NAME, "Tt9ew.pT0Scc"):
                        src = driver.find_element(By.CLASS_NAME, "Tt9ew.pT0Scc").get_attribute(
                            "src"
                        )
                        if src.startswith("http"):
                            st.write("Clicking through Carousel 🎡")
                            # ensure image url is properly formatted
                            src = format_url(src)
                            image_urls.append(src)
                            st.write(f'Valid image found: {src}')
                            break  # A valid image URL was found; exit the loop
                time.sleep(0.5)
            except NoSuchElementException:
                st.write('No image found ❌')
                image_urls.append('https://i.imgur.com/Bs1Tj0Y.png')
                # Continue to the next iteration if element not found
                pass
            except Exception as e:
                # Log other exceptions for debugging
                st.write(f"An error occurred: {e}")
                image_urls.append('https://i.imgur.com/Bs1Tj0Y.png')

        status.update(label=f"{term} search complete!", state="complete", expanded=False)

    df["image_url"] = image_urls
    df = df[['search_term', 'image_url']]

    # merge distinct search terms back to original CSV (which may contain duplicates).
    output_df = og_df.merge(df, how='left', on='search_term')
    image_urls = output_df['search_term'].to_list()
    st.markdown('---')
    for i in image_urls:
        st.markdown(i)



