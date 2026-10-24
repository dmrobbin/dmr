# mysite

Django app: home page with a button that downloads a PDF stored in a private S3 bucket.

## Run locally (PowerShell)
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DJANGO_DEBUG="1"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Then open http://127.0.0.1:8000/ and add a Document at http://127.0.0.1:8000/admin/.
If `pip install` fails on mysqlclient, comment that line out of requirements.txt for now (SQLite is used locally).

## Tests
```
python manage.py test
```
