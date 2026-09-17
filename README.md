# farmer
# 1. Create a python virtual environment named 'venv'
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# to install flask when we see virtual environment (venv)
pip install flask

# Pro Tip to Prevent This in GitHub Codespaces
# To ensure all required packages are saved so you never lose them when restarting Codespaces:
pip freeze > requirements.txt

# Any time you reopen Codespaces or set up a new environment, just run:
pip install -r requirements.txt

==> Available at your primary URL https://agrilink-app-mofe.onrender.com
