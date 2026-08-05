# PythonAnywhere Free Tier Deployment Guide

Hosting your Django application on **PythonAnywhere** is free, simple, and reliable. Since the project is already configured for production, here are the step-by-step instructions to get it running.

---

## Step 1: Clone Your Code from GitHub
First, you'll need to pull the code from your repository using your Personal Access Token (PAT):

1. Log into your **[PythonAnywhere](https://www.pythonanywhere.com/)** account.
2. Open a **Bash Console** from your dashboard.
3. Clone your GitHub repository using your credentials by running:
   ```bash
   git clone https://ArionGD:YOUR_GITHUB_TOKEN@github.com/ArionGD/headhunter.git
   ```

---

## Step 2: Create a Virtual Environment and Install Requirements
In the same PythonAnywhere Bash console, run the following commands:

```bash
# Navigate into the project folder
cd headhunter

# Create a virtual environment using Python 3.10 or 3.11 named 'hunter-env'
mkvirtualenv --python=/usr/bin/python3.10 hunter-env

# Install requirements
pip install -r requirements.txt
```

---

## Step 3: Configure Environment Variables
Create a `.env` file in the root folder of your project on PythonAnywhere to store your API credentials:

1. In the console, run:
   ```bash
   nano .env
   ```
2. Paste your active credentials:
   ```env
   APOLLO_API_KEY=YOUR_APOLLO_API_KEY
   SNOV_CLIENT_ID=YOUR_SNOV_CLIENT_ID
   SNOV_CLIENT_SECRET=YOUR_SNOV_CLIENT_SECRET
   PROSPEO_API_KEY=YOUR_PROSPEO_API_KEY
   ```
3. Press `Ctrl+O` then `Enter` to save, and `Ctrl+X` to exit.

---

## Step 4: Run Collectstatic
Compile your CSS/JS files into the static folder:
```bash
python manage.py collectstatic --noinput
```

---

## Step 5: Configure the Web App on PythonAnywhere
1. Go to the **Web** tab on the PythonAnywhere dashboard and click **Add a new web app**.
2. Select **Manual Configuration** (do not select Django directly, as we already have a custom structure).
3. Choose **Python 3.10** (matching your virtual environment).
4. Under the **Virtualenv** section of your new web app config:
   * Enter the path to your environment: `/home/Cresent/.virtualenvs/hunter-env`
5. Under the **Code** section:
   * **Source code directory**: `/home/Cresent/headhunter`
   * **Working directory**: `/home/Cresent/headhunter`

---

## Step 6: Edit the WSGI Configuration File
1. Under the **Code** section, click the link to edit the **WSGI configuration file** (it looks like `/var/www/cresent_pythonanywhere_com_wsgi.py`).
2. Delete everything inside that file and paste the following configuration:

```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/Cresent/headhunter'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(path, '.env'))

# Set up the WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
3. Save the WSGI file.

---

## Step 7: Configure Static Files (for styling and script rendering)
To ensure the CSS styling renders correctly:
1. Go back to the **Web** tab and scroll down to the **Static files** section.
2. Add a new entry:
   * **URL**: `/static/`
   * **Directory**: `/home/Cresent/headhunter/staticfiles`
3. Click the **Reload** button at the top of the Web tab.

Your dashboard will now be live on `http://cresent.pythonanywhere.com/dashboard/`!
